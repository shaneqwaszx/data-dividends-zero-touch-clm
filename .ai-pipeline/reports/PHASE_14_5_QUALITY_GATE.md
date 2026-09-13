# Phase 14.5 Independent Quality Gate

## 1. Executive Result

**RESULT: FAIL.** This was an independent, pre-Phase-14-integration review. The
implementation handoff and execution report were treated as claims to falsify. The
review confirmed most team, access-control, authentication, session, policy-runtime,
schema, filtering, CSRF, regression, and sponsor-truth behavior, but found three Medium
defects and one Low implementation defect. Physical Mongo verification was also
unavailable because `PHASE12_MONGO_URI` was not configured.

This result does not accept the Phase 14.5 implementation, authorize a checkpoint
commit, authorize Phase 14 integration, or establish PR readiness.

## 2. Reviewer Independence

- Reviewer role: independent quality/security/persistence/POC-regression gate; no Phase
  14.5 implementation work was performed.
- The implementation report's test counts and behavioral assertions were independently
  rerun or attacked.
- The concurrent Phase 14 worktree was not inspected or accessed.
- No finding was remediated. The only repository write made by this review is this
  report.

## 3. Baseline, Main Drift, and Worktree Isolation

| Check | Result | Evidence |
|---|---|---|
| Branch | PASS | `phase/14-5-policy-team-admin` |
| HEAD | PASS | `aba264af3b4088a9a10fe682ee6fc0cb418d550d` |
| `origin/main` at review start | PASS | `aba264af3b4088a9a10fe682ee6fc0cb418d550d` |
| Merge base | PASS | `aba264af3b4088a9a10fe682ee6fc0cb418d550d` |
| `HEAD..origin/main` | PASS | Empty |
| Ambient `PYTHONPATH` | PASS | Unset/zero entries; no forbidden-worktree reference |
| Representative import roots | PASS | `app`, `app.main`, `app.services.authentication`, and `app.services.authorization` all resolved beneath this worktree's `apps/backend/app` tree |

The first bare import probe failed closed because bootstrap hashes were deliberately not
configured. The qualifying import probe used only runtime-generated scrypt test hashes,
forced memory persistence, and a `PYTHONPATH` constructed from this worktree. No local
project module resolved outside this Phase 14.5 worktree.

## 4. Changed-File Classification

The pre-report task-owned surface comprised 53 tracked changes (52 modified, one
deleted), 24 implementation-created files declared in the handoff, and the task-owned
planner. All inspected files were classified; no unexpected scope file was found.

**Intended production/domain/API/persistence/frontend changes:**

- `apps/backend/app/api_auth.py`, `api_models.py`, `api_admin.py`, `api_policies.py`,
  `composition.py`, `config.py`, `main.py`
- `apps/backend/app/domain/access.py`, `domain/models.py`,
  `domain/administration.py`, `domain/policy.py`
- `apps/backend/app/persistence/composition.py`, `persistence/models.py`,
  `persistence/mongo_case_store.py`, `persistence/mongo_admin_store.py`
- `apps/backend/app/services/authentication.py`, `authorization.py`, `case_query.py`,
  `clm_orchestration.py`, `dashboard.py`, `document_processing.py`, `onboarding.py`,
  `ownership_analysis.py`, `reconciliation.py`, `zero_touch_orchestration.py`,
  `admin_repository.py`, `administration.py`, `policy_management.py`
- `apps/frontend/src/App.tsx`, `api.ts`, `types.ts`, `pages/CaseQueue.tsx`,
  `pages/Dashboard.tsx`, `pages/OnboardedClients.tsx`, `pages/PolicyRules.tsx`,
  `pages/AdminTeams.tsx`, `pages/AdminUsers.tsx`, `pages/DirectorTeamFilter.tsx`

**Supporting tests, automation, scripts, and evidence:**

- `.github/workflows/ci.yml`
- `apps/backend/tests/phase13_test_credentials.py`, `test_ownership_api.py`,
  `test_phase12_persistence.py`, `test_phase13_auth_rbac.py`,
  `test_phase13_dashboard.py`, `test_phase13_demo_scripts.py`,
  `test_phase13_mongo_test_safety.py`, `test_phase13_priority.py`,
  `test_phase13_real_mongo.py`, `test_phase14_5_administration.py`,
  `test_phase14_5_case_access.py`, `test_phase14_5_policy.py`,
  `test_phase14_5_real_mongo.py`
- `apps/frontend/src/App.test.tsx`, `Dashboard.test.tsx`,
  `Phase13AuthPriority.test.tsx`, `UiV2Integration.test.tsx`,
  `Phase14_5AdminPolicy.test.tsx`
- `tests/contract/phase13_contract_credentials.py`,
  `tests/test_demo_lifecycle_windows.py`
- deletion of `scripts/generate_phase13_demo_password_hashes.py` and replacement by
  `scripts/generate_admin_bootstrap_password_hashes.py`; modification of
  `scripts/mongo_test_safety.py`
- `.ai-pipeline/001_planner/PHASE_14_5_POLICY_TEAM_IDENTITY_ADMIN.md`,
  `.ai-pipeline/reports/PHASE_14_5_EXECUTION.md`, and the four task-owned Aegis work
  records under `docs/aegis/work/2026-09-09-phase-14-5-policy-team-identity-admin/`

**Intended documentation/contract changes:**

- `docs/PROJECT_CONTEXT.md`, `docs/architecture/README.md`,
  `docs/architecture/PHASE_14_5_POLICY_TEAM_IDENTITY_ADMIN.md`,
  `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md`, `docs/contracts/README.md`,
  `docs/contracts/POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md`,
  `docs/decisions/DECISION_LOG.md`, `docs/demo/DEMO_RUNBOOK.md`,
  `docs/integration/CONFIGURATION_REFERENCE.md`,
  `docs/sponsor-questions/OPEN_QUESTIONS.md`

**Unexpected:** none. No Phase 14 implementation, unrelated case-delete/cache feature,
new dependency, or task-introduced debug marker was found. The pre-existing print calls
in unchanged `apps/backend/app/mongo.py` are baseline-only. Legacy fixed tuples remain
only as compatibility/bootstrap seeds and presentation properties; repository-backed
profiles/teams are the runtime authority.

## 5. Phase Acceptance Checklist

| # | Requirement | Result | Direct evidence |
|---:|---|---|---|
| 1 | `TEAM_A` canonical and displayed as Alpha | PASS | Repository seed/domain/API focused tests |
| 2 | `TEAM_B` canonical and displayed as Beta | PASS | Repository seed/domain/API focused tests |
| 3 | Renames do not migrate existing cases | PASS | Immutable case `team_id`; exact-ID query/access paths |
| 4 | Backend-generated dynamic IDs match `TEAM_<24 uppercase hex>` | PASS | Domain/API adversarial tests; supplied `team_id` rejected 422 |
| 5 | New team gets no Alpha/Beta access | PASS | Gamma RM authenticated and received an empty portfolio |
| 6 | HR role exists | PASS | Typed role and six-account bootstrap |
| 7 | HR has identity/team administration | PASS | Capability map and API authorization tests |
| 8 | HR has zero case access | PASS | Dashboard/list/create 403; existing/absent direct IDs both 404 |
| 9 | HR cannot mutate policies | PASS | All four mutation forms returned 403 |
| 10 | Director/RM can mutate policies | PASS | All four mutation forms returned success for each role |
| 11 | Onboarder/HR policy mutation fails | PASS | All four forms returned fixed 403 |
| 12 | Director filters Cases | PASS | Backend query and frontend transport tests |
| 13 | Director filters Dashboard | PASS | Every metric/list distribution asserted in focused tests |
| 14 | Director filters Onboarded | PASS | Completed subset uses the same backend-authoritative query |
| 15 | Non-Director filter cannot expand scope | PASS | Fixed 403 for team-filter attempts |
| 16 | Dynamic profile repository is auth authority | PASS | Authentication reloads repository account on login/session use |
| 17 | Credentials persist only as scrypt hashes | PASS | Create hashes immediately; safe model/API projections exclude hash |
| 18 | Password/hash absent from browser/audit/log output | PASS | Repr, API, audit, log, and bounded secret checks |
| 19 | Authority change revokes old sessions | PASS | Alpha-to-Beta and team-actor-to-Director probes returned old-session 401 |
| 20 | Security version rejects stale authority | PASS | Session record stores ID/version and reloads current repository account |
| 21 | Existing five synthetic users still work | PASS | Full/focused auth regressions and repository-backed login proof |
| 22 | `hr-admin` bootstrap is safe and POC-only | PASS | Runtime hash requirement, no overwrite, truthful documentation |
| 23 | Typed/bounded policy catalogue | PASS | Exact eight typed rules and hostile DTO validation |
| 24 | Custom rules are showcase-only | PASS | Backend forces `DISPLAY_SHOWCASE_ONLY`; no runtime consumer found |
| 25 | Only IDP and UBO policies run | PASS | Fixed allowlist in `case_snapshot`; no arbitrary catalogue lookup by orchestration |
| 26 | Runtime policy snapshotted at case creation | PASS | Independent threshold-boundary harness |
| 27 | Edits do not reinterpret existing cases | PASS | Old/new cases produced different expected outcomes after edit |
| 28 | Schema v3 supports policy snapshots | PASS | v3 encode/decode and malformed-data tests |
| 29 | v1/v2 readable without read rewrite | PASS | Strict legacy synthesis and input non-mutation tests |
| 30 | Admin persistence separate from case envelopes | PASS | Three dedicated admin collections/repositories |
| 31 | Ordinary tests cannot inherit shared Mongo | PASS | Hostile-environment isolation tests: 10 passed |
| 32 | Phase 13 auth/CSRF/source protections retained | PASS | Full route inventory, origin cardinality, spoofing, and mutation probes |

The checklist does not override the findings below: the last-HR invariant, Mongo
coverage-label uniqueness, and required policy-admin UX remain defective.

## 6. Team and Alpha/Beta Compatibility

`TEAM_A -> Alpha` and `TEAM_B -> Beta` remain exact canonical ID/display mappings in
domain seeds, repository bootstrap, API projections, team options, and case ownership.
Authorization compares exact canonical IDs, never display/coverage names. Lowercase,
malformed, legacy-looking, and client-supplied authoritative IDs were rejected. A
server-generated Gamma team and actor inherited no Alpha/Beta cases; Director retained
global exact-ID visibility. Existing case records are not rewritten on team metadata
change.

## 7. Dynamic Team Access and Team Options

- Gamma creation returned a backend-generated canonical ID.
- A Gamma RM authenticated through the new profile repository and saw zero Alpha/Beta
  cases.
- Director Gamma list/dashboard filters returned an empty exact scope.
- Director and HR receive all active options; RM/Onboarder receive only their current
  active team. Gamma appeared dynamically without source/config changes.
- Director case creation uses freshly fetched options and requires an explicit active
  team.

## 8. HR Case Isolation and Administration

The capability model explicitly gives HR policy view plus identity/team administration,
but no case access/global case capability. Independent API probes returned 403 for HR
Dashboard, case portfolio, and case creation. Existing and nonexistent direct case IDs
both returned 404. Non-HR administration attempts and unauthenticated calls returned
403 and 401 respectively. DTOs reject mass assignment of credential hashes, security
versions, ownership/audit/capability fields, `active`, and supplied team IDs.

Self-demotion was rejected and ordinary stale versions failed closed. However, the
global last-HR condition is not atomic; see P145-QG-001.

## 9. Credential Security and Authentication Migration

- Plaintext passwords exist only in the create-profile request path, are length-bounded,
  immediately converted to salted scrypt hashes, and are not stored in the safe profile.
- `CreateProfileRequest` uses `repr=False`; an independent repr probe did not expose the
  request credential.
- Admin list/create responses omit `credential_hash`; audit metadata contains only safe
  identity/role/team summaries. Authentication logging tests exclude password, hash,
  token, cookie, and CSRF values.
- Unknown-user and wrong-password failures remain generic/equivalent through the dummy
  hash path.
- Runtime authentication loads `ProfileRepository`, and session authentication reloads
  the account/security version rather than trusting a stale profile snapshot.
- Bootstrap uses insert-if-absent and independently preserved an existing stored hash
  when a changed environment hash was supplied.
- The original five users plus `hr-admin` authenticate through the repository-backed
  composition.

## 10. Session Revocation and Capacity

Alpha RM login followed by an HR team change revoked the old cookie (401); re-login
projected Beta. A separate team-actor-to-Director probe returned 200 for the mutation,
set the team to null, rejected the old session with 401, and gave the new Director
session global-route authority. Repository/security-version reload prevents stale
authority after the admin response even if explicit map removal races.

The default capacity is 256 and constructor bounds are 1..1000. An independent probe
created eight repository profiles and held eight simultaneous sessions. Capacity 0 and
1001 were rejected; capacity exhaustion raised the bounded `SessionCapacityError`.
Existing tests independently retained one-session-per-user rotation, concurrent login
serialization, absolute expiry, and expired-session purge.

## 11. Admin CAS and Concurrency

Independent same-version writer probes for team, profile, and policy mutations produced
one success and a conflict for the second writer. Repository updates use expected-version
CAS and do not implement silent browser retries. The policy catalogue is replaced as a
single document. This CAS result does not make the separately non-atomic last-HR count
safe.

## 12. Policy Catalogue and Authorization

The authoritative system catalogue contains exactly the intended eight rules. Values,
types, bounds, classifications, defaults, and enforcement are backend-owned. Only
`DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD` and
`OWNERSHIP_UBO_THRESHOLD_PERCENT` are runtime-enforced; invented scheduler/risk/reviewer
rules were not found.

Authorization matrix observed for create, patch, single reset, and whole reset:

| Actor | Create | Patch | Single reset | Whole reset |
|---|---:|---:|---:|---:|
| RM | 201 | 200 | 200 | 200 |
| Director | 201 | 200 | 200 | 200 |
| Onboarder | 403 | 403 | 403 | 403 |
| HR | 403 | 403 | 403 | 403 |
| Unauthenticated | 401 | 401 | 401 | 401 |

All four authenticated roles could read the catalogue.

## 13. Policy Input Injection

Arbitrary nested JSON, NaN, Infinity, bool-as-integer, excess decimal precision,
overlong strings, excessive lists, unknown fields, direct enforcement/classification,
system metadata, default manipulation, and audit injection all returned 422. Source
search found no `eval`, `exec`, or expression execution, and arbitrary policy IDs are
not runtime-consumed.

Script-looking and expression-looking showcase string values returned 201. They remain
forced display-only and React renders them as escaped text, so no execution sink was
found, but this violates the explicit gate's fail-closed input requirement; see
P145-QG-004.

## 14. Policy Reset, Audit, and Showcase Non-Execution

Backend single reset restored the exact default. Whole reset retained the custom rule,
incremented the catalogue version, added exactly one audit event, and ended with
`POLICY_CATALOGUE_RESET`. Invalid confirmation literals were rejected. Creating/editing
a showcase rule did not change document, ownership, reconciliation, CLM, or zero-touch
runtime selection; source review found only the two fixed runtime IDs entering a case
snapshot.

The frontend whole reset has a confirmation prompt, but per-rule reset does not; custom
showcase rows also receive no edit/reset controls. See P145-QG-003.

## 15. Runtime Policy Snapshot

An independent boundary harness constructed two cases around a policy change and ran
the actual document and ownership services:

- Case A snapshot: IDP `0.85`, UBO `25`, inclusive comparator.
- Case B snapshot: IDP `0.90`, UBO `50`, inclusive comparator.
- Identical field confidence `0.87`: A auto-clear eligible; B not eligible.
- Identical aggregated ownership `40%`: A `MET`; B `NOT_MET`.
- Deliberately contradictory service-constructor defaults were ignored for established
  cases, proving the outcome came from each case snapshot.

Production search found no direct live-global policy lookup during established-case
document, ownership, reconciliation, CLM, or zero-touch processing.

## 16. Schema v1/v2/v3

New durable snapshots encode schema v3. v1 and v2 reads synthesize the explicit legacy
Phase 13 snapshot (`0.85`, `25`, inclusive comparator), produce a v3 in-memory model,
and leave the supplied raw storage value unchanged. v3 preserves the stored snapshot.
Unknown/non-integer schema discriminators, malformed snapshot metadata, invalid team or
priority metadata, and Mongo `_id`/case identity mismatch fail closed. No destructive
bulk migration was found.

## 17. Director Filters and Non-Director Safety

The same backend `CaseQueryService` owns Cases, Dashboard, and completed/Onboarded
filtering. Director filters for all, Alpha, Beta, Gamma, and unassigned use exact team
IDs. Dashboard tests assert filtered total, completed/non-completed, priority totals,
status and priority distributions, recent cases, top active cases, and trend data—not
only visible rows. Onboarded is the completed subset of the selected scope. RM and
Onboarder attempts to supply `team_filter` return fixed 403; HR has no case scope.

## 18. Frontend Role Navigation and Administration UX

Capability-driven navigation gives HR Policy, Users, Teams, and Account while omitting
Dashboard, New onboarding, Cases, Onboarded, and Audit. HR defaults directly to Users,
so case pages are not mounted/fetched. RM sees policy mutation controls, Director gets
policy controls plus server-query team selectors, and Onboarder sees read-only policy.

Profile creation masks both password inputs, confirms locally, clears both values on
success/failure, does not repopulate them, and sends the password only in the unsafe
request. Team creation has no authoritative ID input; the generated ID appears only in
the server-returned row. Profile and team 409 handlers refetch. The policy UI does not
meet the equivalent custom-edit/reset/conflict requirements; see P145-QG-003.

## 19. CSRF, Origin, and Route Inventory

The exact application inventory contains 56 classified routes: two public, 17
actor-only, four case-creation, two case-portfolio, and 31 case-scoped routes. All new
admin/policy unsafe routes are actor-only behind the existing authentication and global
CSRF/browser-source middleware. No new public route was introduced.

Independent probes against admin profile create, admin team create, and policy patch
returned 403 for missing CSRF, wrong CSRF, and foreign Origin, with no mutation.
Qualifying requests succeeded in focused/API tests. Full Phase 13 regressions retained
malformed Origin/Referer, foreign Referer, duplicate physical Origin/Referer, spoofed
Host/forwarded-header, production/dev-origin separation, and route-classification
fail-closed coverage.

## 20. Mongo Static and Physical Review

Static composition uses separate `clm_admin_teams`, `clm_admin_profiles`, and
`clm_admin_policies` collections alongside—not inside—case envelopes. Startup pings,
builds indexes, strictly decodes existing records, and raises on unavailable/invalid
persistence without silently falling back to memory. Team/profile updates filter on ID
and expected version; policy update replaces the versioned singleton. Profile API
projections do not expose credentials, and bootstrap does not overwrite existing
accounts.

Static review found that the Mongo team owner has no normalized coverage-label key,
index, or equivalent atomic uniqueness enforcement, unlike memory mode. See
P145-QG-002.

`PHASE12_MONGO_URI_CONFIGURED = NO`; the value was not read or printed. Physical Mongo
was therefore **SKIPPED**. No Mongo client was pointed at shared `clm_poc`; no physical
database was inspected, written, or cleaned. Restart/persistence/cleanup proof remains
an integration blocker.

## 21. Test Isolation

`test_phase13_test_isolation.py` and `test_phase13_mongo_test_safety.py` completed with
**10 passed in 7.53s**. Their child-process attack supplies hostile parent values for
Mongo mode, a shared-looking database, and a Mongo URI; ordinary composition still
selects memory mode and the ordinary test namespace. Cleanup helpers accept only the
generated phase allowlist and redact driver detail.

## 22. Dependency and Static Checks

| Check | Exact result |
|---|---|
| Dependency diff | NONE across frontend manifests/lockfile and backend requirements/pyproject candidates |
| Ruff | `All checks passed!` for `apps/backend/app apps/backend/tests scripts` |
| Ruff format | 45 explicit added/modified Python files already formatted |
| Mypy | Success: no issues found in 88 source files |
| Pip check | No broken requirements found |

The first mechanically assembled Ruff-format path list included the intentionally
deleted old generator and therefore reported a missing file. Rebuilding the list with
`--diff-filter=AM` plus the explicit new Python files produced the qualifying 45-file
pass. No file was formatted or changed.

## 23. Backend, Frontend, Contracts, and Lifecycle Evidence

| Check | Exact result |
|---|---|
| Focused backend | 135 passed in 39.77s |
| Prescribed runtime-policy command | Failed before collection: `apps/backend/tests/test_reconciliation.py` does not exist; no tests ran |
| Corrected runtime-policy suite | 235 passed in 66.66s using the actual owner `test_phase11_reconciliation.py` |
| Independent runtime snapshot harness | PASS: old/new IDP and UBO boundary outcomes diverged exactly by immutable snapshots |
| Full backend | 919 passed, 13 skipped, 3 known malformed-provider serialization warnings in 183.53s |
| Frontend typecheck | PASS |
| Focused frontend | 1 file, 4 tests passed |
| Full frontend | 5 files, 120 tests passed |
| Frontend production build | PASS; 49 modules transformed |
| Contract suite | 44 tests OK in 1.942s |
| Windows lifecycle | 17 tests OK in 387.108s |
| Secret-scanner unit tests | 5 tests OK |
| Pre-PR-check unit tests | 37 tests OK in 84.067s |
| GoldTier examples | NOT VALIDATED: optional private archives absent |

Frontend Vitest/build and pre-PR/lifecycle subprocesses initially encountered sandbox
process/filesystem restrictions; the qualifying reruns were executed with the required
process permissions and passed. The prescribed runtime-policy filename mismatch is
recorded as P145-QG-005 rather than concealed by the corrected rerun.

## 24. Secret Review

The secret-scanner unit suite passed. To avoid enumerating unrelated/protected untracked
artifacts, `scan_file` was called only for 76 explicit Phase 14.5 modified/created files.
It returned the reported seven syntactic findings. Each exact task-owned line was read
with literal values redacted from tool output and classified independently:

| Path:line | Rule | Classification |
|---|---|---|
| `apps/frontend/src/api.ts:537` | sensitive-assignment | TypeScript request-property type declaration; no value |
| `apps/backend/app/api_admin.py:89` | sensitive-assignment | Bounded request DTO field with `repr=False`; no embedded value |
| `apps/backend/app/api_admin.py:174` | sensitive-assignment | Request-field forwarding to the hashing service; no literal |
| `apps/backend/app/services/administration.py:205` | sensitive-assignment | Method parameter declaration; hashing occurs immediately |
| `apps/backend/tests/test_phase14_5_administration.py:168` | sensitive-assignment | Synthetic, test-local credential used only for create/login/non-disclosure proof |
| `apps/backend/tests/test_phase14_5_real_mongo.py:25` | sensitive-assignment | Helper parameter default referencing runtime-only `TEST_PASSWORD` |
| `apps/frontend/src/Phase14_5AdminPolicy.test.tsx:88` | sensitive-assignment | Synthetic frontend request fixture |

All seven are false positives; no static reusable credential, plaintext production
password, real-looking Mongo URI, exposed credential hash, token, key, or actual secret
assignment was found. The scanner was not weakened. `.env` was not opened.

## 25. Historical and Sponsor Truth

Current docs continue to identify Alpha/Beta as POC presentation names, HR/policy
authority as project-defined rather than sponsor-approved production IAM, and relevant
defaults as pending sponsor confirmation. They distinguish the two runtime policies
from display-only showcase rules and do not imply runtime execution for the latter. No
live ACRA or GoldTier behavior/contract was changed or claimed. Optional private
GoldTier artefacts were absent, so no live/private validation claim is made.

## 26. Phase 14 Future-Conflict Review

Admin domain models, repository protocols, Mongo adapters, services, routers, and
frontend pages are separated. Policy ownership is similarly isolated and arbitrary
runtime consumption is absent. `main.py` is still a 1,880-line integration hotspot but
mostly composes the new routers/services; `App.tsx` is a 2,253-line hotspot but imports
admin/policy components rather than embedding their service logic.

Likely post-Phase-14 merge hotspots are:

- `apps/backend/app/main.py`, `composition.py`, `config.py`
- `apps/backend/app/domain/access.py`, `domain/models.py`
- `apps/backend/app/persistence/composition.py`, `persistence/models.py`,
  `persistence/mongo_case_store.py`
- `apps/backend/app/services/authorization.py`, `case_query.py`, `dashboard.py`, and the
  orchestration services that accept the snapshot
- `apps/frontend/src/App.tsx`, `api.ts`, `types.ts`, case/dashboard/onboarded pages
- `.github/workflows/ci.yml` and shared Phase 13 regression tests

This review did not inspect Phase 14, predict conflict resolutions, merge, or alter
those hotspots.

## 27. Findings

### P145-QG-001 — Medium — Last-HR invariant is non-atomic across profile records

- **Path/contract:** `apps/backend/app/services/administration.py:269`; last-HR safety
  requirement and planner concurrency strategy.
- **Reproduction:** Create two HR accounts and use two authorized HR actors to demote
  each other concurrently. A synchronized repository probe forced both service calls to
  observe the same two-HR snapshot before either per-record CAS. Both writes succeeded;
  the final repository contained zero HR accounts. The existing self-demotion check and
  per-profile version CAS do not protect a cross-record count invariant.
- **Required remediation:** Make “at least one HR remains” an atomic repository-level
  invariant (transaction, global administration lock/version, or equivalent conditional
  write), and add concurrent cross-record demotion tests for memory and physical Mongo.

### P145-QG-002 — Medium — Mongo omits required normalized coverage-label uniqueness

- **Path/contract:** `apps/backend/app/persistence/mongo_admin_store.py:42-53` and
  `:87-112`; planner team uniqueness and memory/Mongo parity requirements.
- **Reproduction:** Static index review shows only a unique
  `normalized_display_name` index. `client_scope_label` is stored without a normalized
  companion/index, and Mongo create/update performs no equivalent check. A fake
  collection faithfully modelling the declared indexes accepted two distinct team IDs
  and names with the same normalized coverage label. Memory mode rejects the same
  collision in `admin_repository.py:105-110`.
- **Required remediation:** Persist a backend-derived normalized coverage-label key and
  enforce it atomically with a unique Mongo index (including safe bootstrap/index
  migration handling), or provide an equivalent atomic uniqueness owner. Add create,
  update, case/whitespace/Unicode collision, and concurrent physical-Mongo parity tests.

### P145-QG-003 — Medium — Policy administration UI does not implement the required mutation workflow

- **Path/contract:** `apps/frontend/src/pages/PolicyRules.tsx:21-57`, `:76-84`, and
  `:126`; planner custom showcase edit/reset, confirmed reset, and 409-refetch behavior.
- **Reproduction:** Create a custom showcase rule through the UI/API. The UI defines
  `editable` only for `RUNTIME_ENFORCED`, so the newly created
  `DISPLAY_SHOWCASE_ONLY` rule has no Save or Reset action even though the backend
  supports both. Per-rule reset sends immediately without user confirmation. Policy
  mutation 409 handlers show an error but do not refetch, and `PolicyRow` local value is
  initialized once and is not synchronized after catalogue reset, allowing a stale
  displayed input.
- **Required remediation:** Implement typed editable controls for allowed showcase
  rules while preserving the non-runtime label, require confirmation for per-rule
  reset, refetch on 409, synchronize row state to server catalogue changes, and add
  focused UI interaction tests for create/edit/single-reset/whole-reset/conflict.

### P145-QG-004 — Low — Script/expression-like showcase strings do not fail closed

- **Path/contract:** `apps/backend/app/domain/policy.py:67-70`, policy create API, and
  the explicit policy-input-injection gate.
- **Reproduction:** Authenticated RM creates using string values resembling a script
  element or expression. Both requests returned 201. Other hostile shapes returned 422.
  No execution sink was found: the rule is forced display-only, React escapes the
  value, and source contains no evaluation path.
- **Required remediation:** Define and enforce the intended safe showcase-string grammar
  (or explicitly revise the gate/contract if escaped arbitrary display text is desired),
  and add API plus rendered-output adversarial tests. Do not add an evaluation path.

### P145-QG-005 — Low — Prescribed runtime-policy regression command names a nonexistent test

- **Path/contract:** Quality-gate instruction AD versus repository test inventory.
- **Reproduction:** The exact prescribed command failed before collection because
  `apps/backend/tests/test_reconciliation.py` does not exist. The actual regression
  owner is `apps/backend/tests/test_phase11_reconciliation.py`; the corrected command
  passed 235 tests.
- **Required remediation:** Update the durable gate/runbook command to the current test
  path so automation cannot report an empty regression execution.

Finding counts: **Critical 0; High 0; Medium 3; Low 2.**

## 28. Required Fixes and Deferred Verification

Current Phase 14.5 fixes required before acceptance:

1. Make the last-HR invariant atomic across records and prove it under concurrency.
2. Enforce normalized coverage-label uniqueness in Mongo with memory/Mongo parity.
3. Complete and test the policy administration UI mutation/reset/conflict workflow.
4. Resolve the showcase script/expression fail-closed contract mismatch.
5. Correct the stale runtime-policy regression command path.

Outstanding external/integration verification, separate from current defects:

- Run only the allowlisted `clm_p145_<24 hex>` physical-Mongo suite when
  `PHASE12_MONGO_URI` is explicitly configured, including restart, persistence,
  no-overwrite, v1/v2/v3, cleanup, and final absence proof.
- Once Phase 14 is accepted onto `origin/main`, merge `origin/main` into this feature
  branch under the repository protocol, resolve the identified hotspots, rerun all
  regressions and `scripts/pre_pr_check.py`, and obtain a new independent post-integration
  re-quality-gate.

## 29. Data-Safety Receipt

| Safety item | Result |
|---|---|
| `.env` accessed | NO |
| Mongo URI/host/credentials printed | NO |
| Shared `clm_poc` inspected | NO |
| Shared `clm_poc` written | NO |
| Concurrent Phase 14 worktree accessed | NO |
| Unrelated protected artifacts accessed | NO |
| Arbitrary untracked artifacts enumerated | NO |
| Implementation modified | NO |
| Files staged/committed/pushed/merged/rebased/reset/stashed/cleaned | NO |

Only explicit task-owned new paths were inspected. Test passwords/hashes, session
tokens, cookies, CSRF values, and Mongo configuration values were not printed in this
report.

## 30. Readiness and Pre-Integration Verdict

- **Pre-integration implementation accepted:** NO.
- **Ready for owner checkpoint commit:** NO.
- **Ready for Phase 14 integration:** NO.
- **Ready for PR:** NO.
- **Physical Mongo:** SKIPPED and still required.
- **Final verdict:** FAIL due to P145-QG-001, P145-QG-002, and P145-QG-003. Even after
  remediation and physical Mongo proof, this branch can receive at most a
  pre-integration acceptance until Phase 14 reaches `origin/main` and a post-integration
  re-QG passes.

## 31. Git Status

At review start, branch/HEAD/main matched the required baseline, no files were staged,
and tracked state contained the owner implementation changes. This report is the only
review-created file. The reviewer did not modify implementation, stage, commit, amend,
push, merge, rebase, reset, stash, clean, or switch branches. Final fetch/SHA/status and
`git diff --check` evidence is captured at closeout in the reviewer response.
