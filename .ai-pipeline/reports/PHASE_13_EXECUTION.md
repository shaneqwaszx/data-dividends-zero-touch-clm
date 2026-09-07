# Phase 13 — Case Prioritisation, Authentication & Team-Based RBAC — Execution Report

## 1. Executive summary

Phase 13 implementation is complete on `phase/13-case-priority-auth-rbac`. The change
adds bounded POC authentication for exactly five synthetic profiles, opaque server-side
sessions, CSRF protection, centralized team authorization, immutable case ownership,
strict nullable priority, schema-v2 persistence, authenticated demo helpers, and UI V2
integration. The accepted Registry -> document -> reconciliation -> ownership -> CLM ->
Mock GoldTier flow remains green.

This is execution evidence, not the independent Phase 13 Quality Gate and not a
production IAM claim.

## 2. Baseline

- Branch: `phase/13-case-priority-auth-rbac`.
- Initial HEAD, local `origin/main`, and merge base:
  `36d0247befce04bbed85e3dced9f9c1c2b617855`.
- Initial tracked changes: none.
- Initial untracked task file: the Phase 13 planner.
- Protected unrelated untracked filename beginning `e workspace and multi-document
  intake`: observed only by `git status --short`; never opened, read, staged, renamed,
  deleted, or otherwise inspected.
- Existing inaccessible pytest-cache artifacts were left untouched.

## 3. Planner compliance

All eight batches in the controlling planner were executed in order. No dependency or
lockfile change was needed. No commit, push, merge, rebase, reset, clean, or branch
switch was performed. Production IAM, reassignment/sharing, role-specific mutation
policy, SLA/escalation behavior, connector contracts, and workflow business rules remain
outside this phase.

## 4. Architecture implemented

- `OnboardingCase` remains the canonical owner of `team_id` and `priority`.
- `AuthenticationService` exclusively owns fixed-profile credential verification and
  process-local sessions.
- `CaseAccessPolicy` exclusively owns server-side visibility and creation-team rules.
- `CaseQueryService` exclusively joins authorized case metadata to automation records
  and applies canonical ordering.
- The existing Phase 12 envelope remains the sole persistence unit; version 2 adds the
  two case fields while a strict, non-writing v1 decoder provides compatibility.
- The frontend uses one in-memory auth context and one request wrapper. It does not
  authorize or sort cases independently.

## 5. Files created

- Backend: `app/domain/access.py`, `app/services/authentication.py`,
  `app/services/authorization.py`, `app/services/case_query.py`, and `app/api_auth.py`.
- Backend tests/support: `tests/conftest.py`, `tests/phase13_test_clients.py`,
  `tests/phase13_test_credentials.py`, `tests/test_phase13_auth_rbac.py`,
  `tests/test_phase13_priority.py`, `tests/test_phase13_real_mongo.py`, and
  `tests/test_phase13_demo_scripts.py`.
- Frontend: `src/auth.tsx`, `src/pages/LoginPage.tsx`,
  `src/pages/PriorityControl.tsx`, and `src/Phase13AuthPriority.test.tsx`.
- Demo: `scripts/generate_phase13_demo_password_hashes.py` and
  `scripts/seed_phase13_demo.py`.
- Documentation: `docs/architecture/PHASE_13_CASE_PRIORITY_AUTH_RBAC.md`,
  `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md`, the three Aegis execution
  records under `docs/aegis/work/2026-09-07-phase-13-auth-rbac/`, and this report.
- Contract-test support: `tests/contract/phase13_contract_credentials.py`.

The pre-existing untracked planner and protected unrelated file are not implementation
outputs.

## 6. Files modified

- Backend runtime/composition: `api_models.py`, `composition.py`, `config.py`,
  `domain/models.py`, `main.py`, `persistence/models.py`,
  `persistence/mongo_case_store.py`, `persistence/repositories.py`,
  `services/clm_orchestration.py`, `services/onboarding.py`,
  `services/repository.py`, and `services/zero_touch_orchestration.py`.
- Existing backend tests: the CLM, document, onboarding, Phase 02, Phase 07, Phase 11,
  Phase 12, pre-Phase-12, and zero-touch modules shown in the final Git audit. Changes
  are limited to authenticated clients, server-owned team creation, and additive
  response assertions.
- Frontend: `App.tsx`, `api.ts`, `main.tsx`, `types.ts`, `viewModels.ts`,
  `styles.css`, the Cases/Case Detail/Onboarded/Audit pages, and the existing App/UI V2
  tests.
- Cross-project tests: two contract modules and the Windows demo lifecycle module now
  provision runtime-random hashes; lifecycle API calls authenticate and send CSRF.
- CI/docs: `.github/workflows/ci.yml`, project context, architecture/contracts indexes,
  decision log, sponsor questions, security boundary, configuration reference, demo
  runbook, and the POC regression catalogue.

## 7. Authentication implementation

Exactly five source-defined synthetic profiles are available. Their five scrypt hashes
must be supplied independently through `SecretStr` environment settings. Missing or
malformed hash configuration fails startup with a fixed error naming only the setting
key. Login performs the same bounded scrypt operation for an unknown user and compares
digests in constant time. No default password, reusable hash, credential file, JWT, or
new dependency was added.

Authentication contract:

- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

Only login and `/health` are public. Every other `/api` endpoint requires a server-
validated session.

## 8. Session/CSRF implementation

Successful login revokes the profile's previous session and issues a 32-byte opaque
token. Only its SHA-256 digest is stored. Sessions have an eight-hour absolute expiry,
one active session per profile, a total bound of five, and purge-on-access/login.
Rotation, logout invalidation, expiry, malformed tokens, capacity handling, and
concurrent same-profile logins are covered by tests. A lock found necessary during the
security review makes session-map updates atomic.

The cookie is host-only, `HttpOnly`, `SameSite=Strict`, `Path=/api`, and secure by
default outside explicit development/test. Production startup rejects an insecure
cookie setting. Unsafe authenticated methods require an in-memory synchronizer token in
`X-CSRF-Token`; same-origin `Origin`/`Referer` values are enforced when present. Login is
JSON-only and same-origin checked.

## 9. User/team/role implementation

Profiles are exactly:

| User | Role | Team | Display scope |
| --- | --- | --- | --- |
| `team-a-onboarder` | Client Onboarder | `TEAM_A` | DBS |
| `team-a-rm` | Relationship Manager | `TEAM_A` | DBS |
| `team-b-onboarder` | Client Onboarder | `TEAM_B` | OCBC |
| `team-b-rm` | Relationship Manager | `TEAM_B` | OCBC |
| `director` | Director | none | All demo scopes |

DBS/OCBC are display metadata only. Authorization compares typed team IDs and obtains
role/team exclusively from the authenticated server profile.

## 10. Central authorization implementation

One default-deny middleware authenticates all `/api` requests and attaches the actor.
One route classifier identifies public, actor-only, case-creation, and case-scoped
families. `CaseAccessPolicy` grants a team actor only exact stored-team matches; Director
can see Team A, Team B, and legacy unassigned cases. Malformed/impossible actors fail
closed. Client role/team headers, query parameters, or frontend state carry no authority.

## 11. Route coverage

The inventory contains 42 routes: 2 public, 5 actor-only, 4 case-creation, and 31
case-scoped routes. Tests compare the application route set to this inventory and run
every case-scoped route family with both a cross-team case ID and an absent case ID.
Coverage includes onboarding, CLM, zero-touch, demo, documents/retries/reviews,
ownership/UBO, readiness/submission, reconciliation/exceptions, start/resume, UAT
evidence, and priority mutation.

## 12. IDOR/non-enumeration behavior

For all 31 case-scoped routes, an inaccessible existing UUID and an absent UUID produce
the same fixed `404 CASE_NOT_FOUND` shape. Cross-team reads and mutations do not expose
case existence or alter data. Missing/malformed/expired sessions receive the same fixed
401 shape; unsafe CSRF/origin failure receives a fixed 403 shape.

## 13. Case-team creation/immutability

Team-scoped creators always receive their authenticated team and cannot provide a team
field. Director must explicitly select Team A or Team B. Legacy v1 cases migrate in
memory to `team_id=null` and remain Director-only. Repository update boundaries enforce
team immutability in memory and Mongo adapters; there is no reassignment endpoint or
heuristic migration.

## 14. Priority implementation

`PATCH /api/clm/zero-touch/cases/{case_id}/priority` accepts only strict JSON integers
`1..10` or `null`. Booleans, floats, strings, out-of-range values, missing fields, and
extra fields are rejected. The mutation runs under the existing per-case lock, persists
the case, and records a safe workflow event. Clearing writes null. A priority mutation
does not change the automation record's timestamp or workflow state.

## 15. Ordering implementation

The backend canonical order is:

1. non-null priority before null;
2. priority descending (`10` highest, `1` above null);
3. automation `updated_at` descending;
4. canonical string `case_id` descending.

Authorization filtering and status filtering occur before this shared sort. Repeated
reads are deterministic. Frontend filtering preserves received order and adds no sort.

## 16. Persistence schema-v2 migration

New and updated envelopes write strict schema version 2. The version-1 model is retained
as an exact strict decoder. Valid v1 data converts in memory to v2 with
`team_id=null`/`priority=null` without writing during read. Unknown versions, malformed
team/priority data, `_id`/`case_id` mismatch, and corrupt nested evidence fail closed.
All existing Phase 12 CAS, revision, recovery, and identity invariants remain active.
The v1 decoder is retained as a bounded persistence compatibility exception for existing
Phase 12 envelopes. Its retirement trigger is an approved migration/decommissioning of
all v1 documents and recoverable backups; Phase 13 performs no live-state rewrite.

## 17. Memory/Mongo parity

Both repository modes consume the same domain fields, access policy, and query/sort
service. Adapter tests cover team immutability, strict migration, priority round trips,
filtering, and ordering. The genuine-Mongo test composes repository set A, writes team
and every priority including null, composes repository set B, verifies provider-free
reads and identical ordering, and is wired into the existing Mongo 7 CI job.

Local genuine-Mongo execution was environment-gated: both Phase 12 and Phase 13 modules
reported 12 skips because no `PHASE12_MONGO_URI` service was configured. This is not
claimed as local PASS; CI is the required genuine-Mongo evidence.

## 18. Demo identities/data

The hash generator prompts twice per profile, uses the production scrypt helper, and
prints hash assignment lines only. The seed helper prompts for the Director credential,
uses only HTTP login/cookie/CSRF APIs, creates or reuses five fixed synthetic UENs per
team, and assigns `10, 8, 5, 1, null` per scope. It never accepts a credential on the
command line, logs one, writes Mongo directly, or embeds real client data. Unit tests
cover generation/seed behavior. A manual seed was not run because operator-configured
demo hashes were not available in this execution environment.

## 19. Frontend authentication

`AuthProvider` restores `/api/auth/me` on load, holds profile and CSRF only in React
memory, renders the login page for anonymous state, and never mounts the workspace
before authentication succeeds. Login/logout are integrated with safe loading/error
states. A centralized 401 callback clears the session shell. No local/session storage or
client-authored role/team is used.

## 20. Frontend priority/RBAC presentation

The header profile menu shows exact display name, role, team, and client scope. Director
case creation requires a Team A/Team B selection; team users do not control team
assignment. Cases, Onboarded, Case Detail, and Audit discovery show scope and priority.
The accessible priority control updates or clears through the protected API and handles
loading plus safe 401/403/404/409/5xx failures. UI V2 layout and existing request/upload
contracts remain covered by 102 frontend tests.

## 21. Security controls

- Credentials: fixed-parameter salted scrypt hashes; constant-time comparison; dummy
  derivation for unknown users; fail-closed configuration.
- Sessions: random opaque bearer, digest-only store, fixed TTL/bounds, rotation,
  revocation, atomic concurrency, no token parsing or logging.
- Browser boundary: strict host-only cookie, production Secure enforcement, same-origin
  deployment, JSON-only login, synchronizer CSRF on unsafe methods, no permissive CORS.
- Authorization: server-authored actors, default-protected `/api`, centralized case
  policy, 404 non-enumeration, immutable team ownership.
- Information handling: fixed safe auth/access errors; no password, hash, cookie, token,
  CSRF, authorization value, KYC, or PII added to logs.

The integration security review found and remediated one medium-severity concurrency
defect in session
rotation. The added adversarial regression demonstrated multiple active same-user
sessions before the lock and exactly one after it. No unresolved critical/high/medium
finding remains within the Phase 13 POC boundary.

## 22. Sponsor questions/provisional rules

Decision D-034 and sponsor question Q-016 record the project-defined behavior pending
confirmation: role differences affect visibility only; any actor with case access may
use existing mutations and change priority; Director has the same mutation surface;
there is no sharing/reassignment; priority affects ordering only; and local credentials/
sessions are POC-only. Q-016 groups the unresolved production permission, priority,
team-sharing/reassignment, SLA, IdP/SSO, RBAC, and identity-governance questions.

## 23. Focused test evidence

- Phase 13 auth/RBAC + priority + Phase 12 persistence + demo scripts: **58 passed**.
- Phase 13/12 genuine-Mongo modules locally: **12 skipped** (Mongo URI unavailable).
- Auth tests include all profiles, startup failure, rotation/expiry/logout, concurrency,
  CSRF/origin, spoofing, creation rules, inventory, and 31-route IDOR equivalence.
- Priority tests include validation, mutation/clear, tie ordering, status filters,
  memory/Mongo-adapter parity, v1 migration, corrupt version/data, and immutability.
- Demo helper tests: included in the 58 focused passes.

## 24. Broad regression evidence

- Full backend suite from `apps/backend`: **802 passed, 12 skipped**, with three existing
  Pydantic serializer warnings in provider-conformance malformed-input tests.
- POC focused catalogue run during Batch 8: **401 passed**; the verified Phase 13
  invariants were then appended to the catalogue.
- Contract suite: **44 passed**.
- Phase 07 delivery assets: **4 passed**.
- Windows lifecycle suite after auth-aware harness update: **17 passed**.
- Frontend: typecheck PASS; **102 passed** across 3 files; production build PASS.
- `npm ls --all`: exit 0; platform/feature optional dependency notices only.
- Ruff: PASS; mypy: PASS across 78 source files; `pip check`: PASS.
- Secret-check unit suite: **5 passed**; repository secret scan: PASS.
- Pre-PR-check unit suite: **37 passed** when rerun with required Windows permissions.
- GoldTier fixture validator retained its accepted baseline:
  `VALID=19`, `INVALID_QUARANTINED=19`, `NOT_VALIDATED=48`.
- `git diff --check`: PASS.

## 25. Mongo evidence

Fast Mongo-adapter parity tests pass inside the backend suite. Genuine restart behavior
could not execute locally without a configured Mongo service and therefore remains an
explicit CI/independent-gate requirement. No live Registry, IDP, Ownership, or GoldTier
provider call is needed by the Phase 13 restart test.

## 26. CI changes

The existing `phase12-mongo` GitHub Actions job still provisions Mongo 7 and now runs
both `test_phase12_real_mongo.py` and `test_phase13_real_mongo.py`. No job, dependency,
manifest, or lockfile was removed or changed.

## 27. Documentation changes

Added the Phase 13 architecture and public access/priority contract; updated project
context, architecture/contracts indexes, D-034, Q-016, security boundaries,
configuration keys, demo hash/seed procedures, and the POC regression catalogue. No raw
sponsor artefact or usable credential material was added.

## 28. Integration hotspots

- `main.py`: route wiring, default auth boundary, server team creation, authorized list,
  and priority endpoint; business workflow handlers otherwise remain intact.
- `api_models.py` / frontend `types.ts`: additive team, scope, priority, profile, and
  priority-mutation contracts.
- `config.py` / `composition.py`: five backend-only secret hashes, cookie mode, and one
  shared auth/policy/query composition.
- Canonical case and persistence models: immutable team, mutable priority, strict v2
  envelope, and controlled v1 read compatibility.
- `api.ts`: cookie credentials, CSRF injection on unsafe methods, and centralized 401
  transition while preserving headers, JSON, polling, and file bodies.
- `App.tsx` and active pages: auth/profile/team/priority presentation only; backend
  remains authoritative.
- CI: the Mongo job's test target was broadened by one Phase 13 module only.

The planned `zero_touch_repository.py` and persistence composition modules did not need
changes: existing automation ordering was reused as the lower-level tie-break, and the
new query service composes above the existing repositories.

## 29. Known limitations

- Authentication is local POC-only: no PingFed/SSO/OAuth/JWT/MFA, registration, reset,
  user administration, durable/distributed sessions, or identity governance.
- Sessions intentionally disappear on backend restart and require login again.
- Team roles intentionally share the same mutation surface; no four-eye or production
  authorization claim is made.
- No case sharing/reassignment or priority-driven SLA/escalation/notification exists.
- Secure cookies require HTTPS outside explicit loopback development/test.
- A manual authenticated seed run requires operator-provisioned hashes and was not
  possible in this environment.

## 30. Remaining blockers/risks

- Genuine Mongo 7 restart evidence must pass in CI and the independent gate; local
  absence is the only implementation-environment blocker.
- The grouped sponsor production-policy questions remain intentionally open.
- The optional Aegis workspace helper/process baselines are not installed in this
  repository, so the hand-authored work record could not be helper-bundled or
  structurally checked. This affects process-record structure only, not product tests.
- `origin/main` must be freshly fetched/checked and integrated only when separately
  authorized before PR readiness.
- The independent Phase 13 Quality Gate has not run.

## 31. Git status/diff audit

The final audit shows only Phase 13 implementation/docs/tests, the pre-existing planner,
the protected unrelated untracked file, and pre-existing inaccessible pytest-cache
artifacts. No connector module, GoldTier/ACRA contract or mapper, package manifest,
lockfile, raw sponsor artefact, `.env`, or credential material changed. No file was
staged or committed. Line-ending warnings are working-copy notices, not content errors;
`git diff --check` passes.

## 32. Quality Gate readiness

**IMPLEMENTATION COMPLETE; INDEPENDENT GATE PENDING.** The implementation is ready for
the Phase 13 independent review after genuine Mongo CI evidence and the authorized
latest-main integration step. `python scripts/pre_pr_check.py` was intentionally not run:
it requires committed feature work and a clean tree, while this execution was explicitly
required to remain dirty and uncommitted. Its own unit suite passed 37 tests, but that is
not represented as pre-PR readiness.

## 33. Bounded independent-quality-gate remediation

This section records only the remediation of `P13-QG-001` through `P13-QG-004`. The
independent quality-gate report was not modified, and no Phase 13 capability, external
connector, dependency, or business rule was added.

### P13-QG-001 — strict Mongo schema discriminator

- **Finding:** non-integer equality lookalikes could select the v1/v2 decoder.
- **Root cause:** Python equality makes `True == 1` and accepts integral floats such as
  `1.0 == 1`; the outer discriminator did not first enforce the exact runtime type.
- **Files changed:** `apps/backend/app/persistence/mongo_case_store.py` and
  `apps/backend/tests/test_phase13_priority.py`.
- **Fix:** require `type(schema_version) is int` before branching; exact integer `1`
  continues through the strict, non-writing v1 decoder, exact integer `2` through the
  strict v2 decoder, other integers through the unsupported-schema failure, and every
  non-integer through the malformed-persistence failure.
- **Tests added:** direct raw-envelope coverage for `True`, `False`, `1.0`, `2.0`,
  `1.5`, strings, null, list, dict, and another non-integer object, plus positive raw
  integer v1/v2 cases.
- **Verification:** focused persistence selection passed; the complete backend suite
  passed **815 tests** with **12 genuine-Mongo environment skips**.
- **Status:** **CLOSED**.

### P13-QG-002 — authoritative frontend refetch and timestamp semantics

- **Finding:** priority mutation patched rows in place, preserving stale positions and
  substituting case-mutation time where the list field means automation-update time.
- **Root cause:** the shared priority control returned mutation-response values to page
  state owners, which treated them as authoritative list/detail projections.
- **Files changed:** `apps/frontend/src/pages/PriorityControl.tsx`,
  `apps/frontend/src/pages/CaseQueue.tsx`,
  `apps/frontend/src/pages/OnboardedClients.tsx`,
  `apps/frontend/src/pages/CaseDetail.tsx`, and
  `apps/frontend/src/Phase13AuthPriority.test.tsx`.
- **Fix:** after a successful mutation, queue and onboarded pages refetch their current
  authoritative backend lists and replace visible rows in server order; Case Detail
  refreshes its authoritative evidence/detail projection. Existing filters and actor
  session remain in place. No client priority sorter or full-page reload was added, and
  mutation `case.updated_at` is not written into list `automation.updated_at` state.
- **Tests added:** an initial `A(10), B(1), C(null)` projection, `C -> 9` mutation, and
  `A(10), C(9), B(1)` refetch are rendered in returned order; a distinct mutation time
  proves C retains the server-list automation timestamp.
- **Verification:** focused Phase 13 frontend suite passed **7/7**; full frontend suite
  passed **103/103**; typecheck and the production build (45 modules) passed.
- **Status:** **CLOSED**.

### P13-QG-003 — genuine-Mongo raw-v2 and physical immutability assertions

- **Finding:** the environment-gated genuine-Mongo test proved restart projection but
  did not inspect raw schema v2 or attempt a physical repository team mutation.
- **Root cause:** coverage stayed at API/recomposition level and omitted the raw Mongo
  envelope plus physical persistence rejection boundary.
- **Files changed:** `apps/backend/tests/test_phase13_real_mongo.py`.
- **Fix:** inspect each persisted Mongo document and require an exact integer schema
  version `2`; load through the physical persistence bundle, attempt `TEAM_A -> TEAM_B`,
  require `CaseTeamImmutableError`, and prove raw and decoded state still retain TEAM_A
  and priority 10 before and after composition restart. Existing Team A/Team B/null
  priority/order/provider-free restart checks remain.
- **Tests added:** raw-envelope v2 assertions, repository-level immutable-team adverse
  mutation, unchanged physical reload, and post-restart raw team/priority/v2 assertions.
- **Verification:** test collection and environment-gated execution are healthy, but
  the test was **SKIPPED**, not passed: `PHASE12_MONGO_URI` is absent and Docker reports
  no running Linux engine. **GENUINE MONGO EVIDENCE: UNAVAILABLE.**
- **Status:** **CLOSED** for the missing assertions; physical execution evidence remains
  an explicit requirement for the subsequent independent re-quality gate.

### P13-QG-004 — exact recursive route inventory

- **Finding:** the regression observed only top-level `APIRoute` objects and accepted a
  subset, so an included unclassified route might escape the assertion.
- **Root cause:** test collection did not flatten included/deferred router nodes and did
  not compare both directions.
- **Files changed:** `apps/backend/tests/test_phase13_auth_rbac.py`.
- **Fix:** recursively collect the actual mounted application route graph, including
  included-router nodes, and require exact equality with the authoritative inventory.
  Counts remain exactly 2 public, 5 actor-only, 4 case-creation, 31 case-scoped, and 42
  total.
- **Tests added:** a temporary test-only included router adds an unclassified `/api`
  route and proves the exact comparison rejects the augmented inventory.
- **Verification:** focused route-inventory selection passed **2/2**; the broader Phase
  13/12 focused selection passed **69 tests** with **1 real-Mongo skip**.
- **Status:** **CLOSED**.

## 34. Remediation verification evidence

- Focused backend (`test_phase13_auth_rbac.py`, `test_phase13_priority.py`,
  `test_phase13_real_mongo.py`, `test_phase12_persistence.py`, cache disabled):
  **69 passed, 1 skipped**; the skip is the explicit absent-Mongo environment gate.
- Full backend: **815 passed, 12 skipped**, with the three existing adversarial
  Pydantic serializer warnings.
- Current POC regression catalogue selection: **456 passed, 1 skipped**, with the same
  three warnings. All accepted call-stopping, terminal-state, identity, isolation,
  server-authored ordering, and truthful Mock/Sandbox labeling assertions passed; the
  catalogue itself required no change.
- Ruff: PASS. Mypy: PASS across 78 source files. `pip check`: PASS.
- Contract discovery: **44 passed**.
- Frontend dependency tree: exit 0 with optional platform/feature dependency notices;
  typecheck PASS; Vitest **103 passed**; production build PASS (45 modules).
- Windows demo lifecycle: **17 passed** and owned processes were stopped.
- Secret-check unit suite: **5 passed**. The repository scanner was intentionally not
  run over the protected unrelated untracked file during this bounded remediation.
- Pre-PR-check unit suite: **37 passed**. The production pre-PR checker was intentionally
  not run against this required dirty, uncommitted tree.
- Genuine Mongo availability probe: URI absent; Docker client 29.7.2 present; Docker
  Linux engine unavailable. **GENUINE MONGO EVIDENCE: UNAVAILABLE.**

Remediation introduced no dependency, connector, ACRA/GoldTier business-rule,
authentication-policy, team-policy, or schema-shape change beyond the required exact
schema-discriminator validation. No file was staged, committed, pushed, merged,
rebased, reset, cleaned, or branch-switched.
