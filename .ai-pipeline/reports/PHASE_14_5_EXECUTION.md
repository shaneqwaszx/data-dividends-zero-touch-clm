# Phase 14.5 Execution Report — Policy, Team, and Identity Administration

## Baseline and outcome

- Branch: `phase/14-5-policy-team-admin`
- Baseline/HEAD: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
- Final fetched `origin/main`: `b8f9406b57929c7ede537b0262ea78f655b48c27`
- Main drift: yes; Phase 14 is merged on `origin/main` and integration remains deferred.
- Outcome: all seven implementation slices completed. The independent quality gate
  reported five targeted findings; P145-QG-001 through P145-QG-005 are remediated and
  closed by independent re-QG. P145-PHYS-001 is closed by the independent physical
  re-quality gate using owner-supplied restart-and-cleanup evidence.

## Architecture implemented

Global administration now has focused domain, service, repository, API, and Mongo
owners separate from case envelopes. `TEAM_A` and `TEAM_B` retain their persisted IDs
and display as Alpha and Beta. New teams use server-generated
`TEAM_<24 uppercase hex>` IDs. Runtime identity authority moved from the fixed profile
tuple to profile repositories; bootstrap definitions remain insert-only seed input.

The backend capability matrix adds HR as an administration-only role. HR can create and
update profiles/teams, but has no case or policy-mutation authority. Director remains
global for cases and may filter Cases, Dashboard, and Onboarded Clients by all teams,
dynamic teams, or legacy unassigned cases. Team-scoped actors continue to use exact
stored team-ID equality.

Authentication preserves opaque process-local sessions, rotation, one active session
per user, dummy-hash unknown-user behavior, generic failures, session CSRF, cookies,
and Origin/Referer enforcement. Sessions retain a `user_id` and `security_version`, not
an authoritative permanent profile snapshot. Role/team changes increment the version,
explicitly revoke sessions, and cause any racing stale cookie to receive `401`.

Mongo administration uses `clm_admin_teams`, `clm_admin_profiles`, and
`clm_admin_policies` with the exact approved indexes. Memory repositories provide the
same defensive-copy, locking, unique-name, CAS, and audit-integrity behavior. Bootstrap
inserts six identities only when absent; persisted hashes remain authoritative.

Profile authority changes now use one repository-owned atomic mutation. The memory
owner holds one repository-wide `RLock` across target/version load, self-demotion and
HR-population checks, and version/security-version/audit commit. The Mongo owner holds
the shared administration store's process-local lock across target load, HR count, and
target expected-version CAS. This guarantees at least one HR inside the supported
single-process POC application boundary; it is not distributed or multi-instance IAM
atomicity. A barrier-synchronized cross-demotion test produced exactly one success,
one bounded rejection, and a final HR count of one.

Every team now persists backend-derived `normalized_display_name` and
`normalized_client_scope_label`. Memory rejects either collision and Mongo declares a
unique index for each, retaining `(active, display_name)`. Startup strictly decodes
records before index creation, malformed/missing keys fail closed, and duplicate-key
detail maps to the bounded administration conflict. Alpha/Beta IDs and labels remain
unchanged.

## Policy and case behavior

The strict global catalogue seeds the exact eight approved POC rules, supports CAS
updates and single/catalogue reset, and limits mutation to RM and Director. Client
Onboarder and HR are read-only. User-created rules are forced to display/showcase-only
and cannot become runtime policy. Audit events are allowlisted, append-only, bounded at
256, and contain no password, hash, session, CSRF, URI, or model dump.

User-authored showcase scalar strings and every string-list item use the strict
plain-text grammar `^[A-Za-z0-9][A-Za-z0-9 _./:+%-]{0,127}$` plus code-like prefix
rejection. Script/expression punctuation fails closed while ordinary values including
`Enhanced Review`, `MANUAL_REVIEW`, `Level-2`, `SG`, `ACRA`, `25%`, `Risk: Medium`,
and `application/pdf` remain valid. System-owned typed enum/list values are unaffected,
and showcase values still have no runtime execution path.

Only the IDP confidence and UBO percentage rules affect runtime. New cases bind those
values, the fixed inclusive comparator, catalogue version/label, and UTC timestamp in
an immutable `CasePolicySnapshot` before registry work. Later policy changes affect
only later cases. New persistence writes use strict schema v3; exact v1/v2 readers stay
available, synthesize the immutable legacy `0.85`/`25.000000` policy snapshot in
memory, and do not rewrite on read.

## API and UI surface

Added authenticated team options; HR team/profile list/create/update routes; and
policy catalogue read/create/update/reset routes. The route inventory covers all new
endpoints. Browser-safe responses exclude credentials. Frontend navigation is
capability-driven, adds Users and Teams administration, uses backend team options for
Director filters, and replaces the derived Policy page with the persisted catalogue.
Custom rules remain visibly showcase-only/non-runtime but now expose the backend-
permitted edit and reset actions to RM/Director. Single and whole reset use accessible
`alertdialog` confirmation, Cancel/Escape issue no mutation, and confirm is guarded
against duplicate submission. A policy `409` performs one authoritative catalogue
refetch, closes/invalidates stale edit state, and never retries the stale mutation.
Client Onboarder and HR remain read-only.

## Independent-QG remediation

- **P145-QG-001 CLOSED:** `ProfileRepository.mutate_authority` owns the serialized
  last-HR invariant, self-demotion rule, security/version increment, and audit commit.
  Memory concurrency and existing session-revocation regressions pass. Mongo uses the
  same store-local lock boundary plus target CAS; the later independent physical gate
  accepted owner restart-and-cleanup evidence.
- **P145-QG-002 CLOSED:** `normalized_client_scope_label` is strict and backend-derived;
  create/update whitespace, case, and Unicode collisions fail in memory. Mongo has the
  unique index and safe duplicate-key mapping; bootstrap records contain both keys and
  strict startup decode precedes index creation.
- **P145-QG-003 CLOSED:** the production Policy screen implements custom edit, confirmed
  single/whole reset, zero-network cancellation, duplicate-submit protection, 409
  refetch/no-retry, authoritative row-state synchronization, and read-only roles. The
  focused file contains 22 policy workflow cases plus four existing admin/filter cases.
- **P145-QG-004 CLOSED:** the canonical user-authored showcase string validator rejects
  the specified hostile scalar/list values and accepts normal display values without
  changing runtime policy behavior.
- **P145-QG-005 CLOSED:** Planner command superseded by current repository test owner:
  `apps/backend/tests/test_phase11_reconciliation.py`. The planner and historical QG
  remain unchanged.

## Targeted physical-Mongo remediation

- **P145-PHYS-001 CLOSED:** persisted profile documents use
  `user_id` as Mongo `_id`, but the shared administration decoder previously selected
  `team_id` before `user_id` when validating storage identity. A valid seeded
  Onboarder or Relationship Manager therefore decoded successfully as a model and was
  then rejected because `TEAM_A`/`TEAM_B` did not equal its user-ID `_id` during
  restart initialization.
- The decoder now selects the identity explicitly by record type: `team_id` for
  `TeamRecord`, `user_id` for `UserAccountRecord`, and `catalogue_id` for
  `PolicyCatalogue`. Unknown model types and corrupt, unknown-field, or mismatched-ID
  documents continue to fail closed.
- A structural codec regression round-trips seeded Onboarder, Relationship Manager,
  Director, and HR profiles plus a newly created Relationship Manager. It preserves
  `user_id`, role, optional `team_id`, `security_version`, and the credential hash;
  the test compares credential material without rendering or logging it.
- The independent physical re-quality gate accepted owner evidence of
  `tests/test_phase14_5_real_mongo.py`: `1 passed in 33.03s`, including restart and
  generated-database cleanup. This targeted API-typing remediation does not touch
  persistence, composition, or persisted administration/policy models.

## Targeted mypy remediation

- The initial full `mypy app` result contained 26 findings in `api_admin.py` and
  `api_policies.py`: 12 `no-untyped-call`, 12 `no-any-return`, and two
  `no-untyped-def` findings. Each stemmed from an untyped exception-mapping helper,
  which caused its handler closure result to become `Any`.
- Both helpers now use a Python 3.12 generic function signature,
  `Callable[[], ResponseT] -> ResponseT`. The type invariant matches runtime behavior:
  the helper either returns the closure's exact value or raises the existing bounded
  `HTTPException`. No ignore, `Any`, cast, validation, RBAC, team, policy, or HTTP
  behavior change was introduced.

## Verification

- Previous focused backend: 171 passed. New codec regression slice: 2 passed.
- Focused administration: 20 passed. Focused policy: 38 passed.
- Last-HR adversarial slice: 4 passed, 14 deselected.
- Policy-injection slice: 22 passed, 16 deselected.
- Runtime-policy regression chain: 235 passed.
- Targeted mypy remediation focused suite: 125 passed across Phase 14.5
  administration/policy, Phase 13 auth/RBAC, and test-isolation coverage.
- Full backend: 957 passed, 13 skipped, 3 pre-existing Phase 06 Pydantic serializer
  warnings in 83.57s with the worktree-local backend path pinned for child-process
  import isolation.
- Frontend: focused 26 passed (22 policy workflow plus four administration/filter);
  typecheck passed; full 142 passed; production build passed (49 modules, 258.80 kB JS
  and 59.14 kB CSS before gzip).
- Contracts: 44 passed.
- Windows lifecycle: final run 17 passed.
- Secret scanner units: 5 passed.
- Pre-PR helper units: 37 passed; `scripts/pre_pr_check.py` was not executed.
- Ruff lint: `All checks passed!` for `app` and `tests`. Both changed API routers are
  formatted. Full `ruff format --check app tests` still reports 26 unrelated pre-existing
  unformatted files; no repository-wide formatting was performed. Full `mypy app`:
  `Success: no issues found in 88 source files`. Pip check: passed.
- `git diff --check`: passed.
- Physical Mongo: independently accepted owner evidence, `1 passed in 33.03s`; this
  API-typing remediation did not require a rerun and `.env` was not opened.

## Security, data, and dependency safety

No plaintext password, credential hash, session, CSRF, Mongo URI, or provider payload
is returned or added to audit/log output. The remediation-bounded scan covered 20 exact
task-owned files and returned nine value-suppressed syntactic matches (typed password
fields, variable references, and test-only credentials); manual review found no secret
material. Shared `clm_poc` was neither
inspected nor written. Physical tests remain allowlisted to
`^clm_p145_[0-9a-f]{24}$`. No dependency manifest or lockfile changed.

During the original implementation pass, the first unscoped Python test command
resolved `app` through ambient import state to the prohibited concurrent Phase 14
worktree and failed during collection; no implementation file there was opened,
inspected, copied, or modified. The remediation import-isolation probe generated
runtime-only bootstrap hashes, forced memory persistence, imported `app`, `app.main`,
authentication, and authorization, and confirmed every module path is beneath this
Phase 14.5 worktree. Every remediation Python invocation used the explicit
worktree-local backend path, and the prohibited Phase 14 worktree was not accessed
during remediation.

## Files and integration hotspots

Created focused backend administration/policy domain, service, API, persistence, and
test files; frontend Users/Teams/filter components and tests; current architecture and
contract documents; the six-user bootstrap hash generator; this report; and Aegis work
evidence. Modified authentication, authorization, composition, case persistence,
runtime threshold consumers, Dashboard/query projections, current frontend
composition/types, CI Mongo coverage, current docs, test credential helpers, and Mongo
safety. Retired `scripts/generate_phase13_demo_password_hashes.py` after replacing all
current tracked consumers with `scripts/generate_admin_bootstrap_password_hashes.py`.

Future Phase 14 integration hotspots are:

- `apps/backend/app/main.py`
- `apps/backend/app/api_models.py`
- `apps/backend/app/domain/models.py`
- `apps/backend/app/persistence/models.py`
- `apps/backend/app/persistence/mongo_case_store.py`
- `apps/backend/app/persistence/composition.py`
- `apps/backend/app/services/authorization.py`
- `apps/backend/app/services/case_query.py`
- `apps/frontend/src/App.tsx`
- `apps/frontend/src/api.ts`
- `apps/frontend/src/types.ts`
- `.github/workflows/ci.yml`

## Remaining risks and next step

Repository-wide format debt remains outside this targeted remediation. The backend
`main.py` composition root is materially oversized; this phase added wiring only and a
separate authorized decomposition should own that debt. Phase 14 is now ahead on
`origin/main`; integration remains explicitly deferred.

Next: owner checkpoint commit, then a separately authorized Phase 14 integration pass
across the hotspots above; do not rebase or merge during this implementation handoff.

## File inventory

Created by this implementation:

- `.ai-pipeline/reports/PHASE_14_5_EXECUTION.md`
- `apps/backend/app/api_admin.py`
- `apps/backend/app/api_policies.py`
- `apps/backend/app/domain/administration.py`
- `apps/backend/app/domain/policy.py`
- `apps/backend/app/persistence/mongo_admin_store.py`
- `apps/backend/app/services/admin_repository.py`
- `apps/backend/app/services/administration.py`
- `apps/backend/app/services/policy_management.py`
- `apps/backend/tests/test_phase14_5_administration.py`
- `apps/backend/tests/test_phase14_5_case_access.py`
- `apps/backend/tests/test_phase14_5_policy.py`
- `apps/backend/tests/test_phase14_5_real_mongo.py`
- `apps/frontend/src/Phase14_5AdminPolicy.test.tsx`
- `apps/frontend/src/pages/AdminTeams.tsx`
- `apps/frontend/src/pages/AdminUsers.tsx`
- `apps/frontend/src/pages/DirectorTeamFilter.tsx`
- `docs/aegis/work/2026-09-09-phase-14-5-policy-team-identity-admin/10-intent.md`
- `docs/aegis/work/2026-09-09-phase-14-5-policy-team-identity-admin/20-checkpoint.md`
- `docs/aegis/work/2026-09-09-phase-14-5-policy-team-identity-admin/90-evidence.md`
- `docs/aegis/work/2026-09-09-phase-14-5-policy-team-identity-admin/99-reflection.md`
- `docs/architecture/PHASE_14_5_POLICY_TEAM_IDENTITY_ADMIN.md`
- `docs/contracts/POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md`
- `scripts/generate_admin_bootstrap_password_hashes.py`

Modified:

- `.github/workflows/ci.yml`
- `apps/backend/app/api_auth.py`
- `apps/backend/app/api_models.py`
- `apps/backend/app/composition.py`
- `apps/backend/app/config.py`
- `apps/backend/app/domain/access.py`
- `apps/backend/app/domain/models.py`
- `apps/backend/app/main.py`
- `apps/backend/app/persistence/composition.py`
- `apps/backend/app/persistence/models.py`
- `apps/backend/app/persistence/mongo_case_store.py`
- `apps/backend/app/services/authentication.py`
- `apps/backend/app/services/authorization.py`
- `apps/backend/app/services/case_query.py`
- `apps/backend/app/services/clm_orchestration.py`
- `apps/backend/app/services/dashboard.py`
- `apps/backend/app/services/document_processing.py`
- `apps/backend/app/services/onboarding.py`
- `apps/backend/app/services/ownership_analysis.py`
- `apps/backend/app/services/reconciliation.py`
- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/tests/phase13_test_credentials.py`
- `apps/backend/tests/test_ownership_api.py`
- `apps/backend/tests/test_phase12_persistence.py`
- `apps/backend/tests/test_phase13_auth_rbac.py`
- `apps/backend/tests/test_phase13_dashboard.py`
- `apps/backend/tests/test_phase13_demo_scripts.py`
- `apps/backend/tests/test_phase13_mongo_test_safety.py`
- `apps/backend/tests/test_phase13_priority.py`
- `apps/backend/tests/test_phase13_real_mongo.py`
- `apps/frontend/src/App.test.tsx`
- `apps/frontend/src/App.tsx`
- `apps/frontend/src/Dashboard.test.tsx`
- `apps/frontend/src/Phase13AuthPriority.test.tsx`
- `apps/frontend/src/UiV2Integration.test.tsx`
- `apps/frontend/src/api.ts`
- `apps/frontend/src/pages/CaseQueue.tsx`
- `apps/frontend/src/pages/Dashboard.tsx`
- `apps/frontend/src/pages/OnboardedClients.tsx`
- `apps/frontend/src/pages/PolicyRules.tsx`
- `apps/frontend/src/types.ts`
- `docs/PROJECT_CONTEXT.md`
- `docs/architecture/README.md`
- `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md`
- `docs/contracts/README.md`
- `docs/decisions/DECISION_LOG.md`
- `docs/demo/DEMO_RUNBOOK.md`
- `docs/integration/CONFIGURATION_REFERENCE.md`
- `docs/sponsor-questions/OPEN_QUESTIONS.md`
- `scripts/mongo_test_safety.py`
- `tests/contract/phase13_contract_credentials.py`
- `tests/test_demo_lifecycle_windows.py`

Retired: `scripts/generate_phase13_demo_password_hashes.py`.

Pre-existing untracked task input preserved:
`.ai-pipeline/001_planner/PHASE_14_5_POLICY_TEAM_IDENTITY_ADMIN.md`.
