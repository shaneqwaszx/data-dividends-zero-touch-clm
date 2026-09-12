# Phase 14.5 — Policy, Team & Identity Administration

**Goal:** Replace the fixed Phase 13 team/profile presentation with a bounded,
backend-authoritative administration model that preserves `TEAM_A`/`TEAM_B` case
ownership, adds HR-only identity/team administration, adds typed policy administration,
and gives Director a server-enforced team filter.

**Architecture:** Add one application-level administration boundary with repository
interfaces and memory/Mongo implementations for teams, profiles/credential hashes, and
the global policy catalogue. Keep case authorization in the existing central boundary,
bind runtime policy values into an immutable per-case snapshot at case creation, and
project only safe administration metadata to the browser.

**Tech stack:** Python 3.12, FastAPI, Pydantic v2, PyMongo, process-local opaque
sessions, scrypt credentials, React 18, TypeScript 5.9, Vitest, MongoDB 7 physical tests.

**Baseline/Authority Refs:** `AGENTS.md`; `docs/PROJECT_CONTEXT.md` (accepted Phase 13
state); `docs/architecture/PHASE_13_CASE_PRIORITY_AUTH_RBAC.md`;
`docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md`; decisions D-020, D-021, D-025,
D-033 through D-039 in `docs/decisions/DECISION_LOG.md`; Q-004, Q-014, Q-015, and Q-016
in `docs/sponsor-questions/OPEN_QUESTIONS.md`; the owner requirements supplied for this
planner; and the final accepted Phase 13 evidence in
`.ai-pipeline/reports/PHASE_13_DUPLICATE_BROWSER_SOURCE_FINAL_REQUALITY_GATE.md`.

**Compatibility Boundary:** Persisted case ownership identifiers `TEAM_A` and `TEAM_B`,
all five Phase 13 synthetic user IDs, current case access/non-enumeration rules, opaque
server-side sessions, cookie/CSRF/Origin/Referer protections, case-team immutability,
schema-v1/v2 reads, Mock/live truth labels, and provider-free historical reads must
remain valid. No existing case is reassigned or reinterpreted because a label, profile,
team, or policy changes.

**TDD Route:**

- Mode: `off` (observed in the local Aegis configuration).
- Decision: `skipped`.
- Strict authority: not applicable; neither the user nor project rules require strict
  test-first sequencing.
- Strict signals: authorization, credentials, persistence, schema migration, policy
  binding, and producer/consumer contract changes are high-risk signals, but do not
  override `tdd_mode = off`.
- Light eligibility: not eligible; this is a cross-module behavior and persistence
  change.
- TDD-fit exception: none.
- Test posture: implement each minimum bounded slice, then run its focused regression
  and the adverse tests listed in this plan.
- Reason: project rules require meaningful tests but do not prescribe RED/GREEN order.
- Verification: focused backend/frontend/Mongo tests after every slice, then the full
  quality checklist in section 34.

**Verification:** The implementation agent must prove exact role/capability behavior,
dynamic-team zero-access invariants, non-disclosure, session revocation, policy CAS and
reset behavior, per-case policy binding, schema compatibility, memory/Mongo parity,
and all existing Phase 13 auth/RBAC regressions before handoff.

---

## 1. Executive summary

Phase 14.5 should not extend the current tuples and enums. The smallest sufficient
stable design is a typed administration domain backed by three global persistence
owners: teams, profiles, and a singleton policy catalogue. `TEAM_A` and `TEAM_B` remain
canonical IDs and are seeded as Alpha and Beta. New teams receive server-generated IDs
of the form `TEAM_<24 uppercase hex characters>`; browser-supplied IDs are never accepted
by team creation.

The five accepted Phase 13 identities are seeded into the profile repository without
changing their user IDs or internal team IDs. A sixth synthetic POC-only bootstrap
identity, `hr-admin` / `POC HR Administrator`, is seeded with role `HR`, no team, and an
environment-supplied scrypt hash. HR can administer users and teams but has no case
access and no policy mutation authority. Director retains global case access and gains
an optional team filter across Cases, Dashboard, and Onboarded. Relationship Manager
and Director can mutate policies; all authenticated roles can read them.

Only two current policy values become editable and runtime-active: the IDP review
confidence threshold and UBO ownership threshold. Both remain project defaults pending
sponsor confirmation. They are snapshotted on new case creation. Existing cases use an
explicit immutable Phase 13 legacy snapshot (`0.85`, `25`, inclusive comparator), so a
later policy edit never retroactively changes their decisions. User-created rules are
forced by the backend to `DISPLAY_SHOWCASE_ONLY` and cannot execute code or influence
workflow.

No application code is changed by this planner. The only planner artifact is this file.

## 2. Verified current architecture

The following is observed at baseline
`aba264af3b4088a9a10fe682ee6fc0cb418d550d`:

- `apps/backend/app/domain/access.py` owns fixed `TeamId` and `Role` `StrEnum`s, a
  two-entry `TEAMS` tuple/`TEAM_BY_ID` map, and five fixed
  `SYNTHETIC_USER_PROFILES`.
- `apps/backend/app/services/authentication.py` constructs credentials from those five
  profiles, retains a full actor/profile snapshot in each process-local session, allows
  one session per user, and incorrectly derives total session capacity from the fixed
  profile count.
- `apps/backend/app/config.py` defines five optional Phase 13 hash settings. The
  composition layer requires all five at startup and passes them to the authentication
  service.
- `apps/backend/app/api_auth.py` derives team metadata and Director team options from
  the global fixed team map. Login is the only public `/api` route; all protected unsafe
  routes receive the accepted central CSRF and Origin/Referer checks.
- `apps/backend/app/services/authorization.py` is the central case access and route
  inventory owner. Director is global; all other roles are implicitly treated as team
  actors. Actor-only list and Dashboard routes currently need no role guard.
- `apps/backend/app/services/case_query.py` applies canonical case authorization before
  status/priority filtering. It has no Director team filter.
- `apps/backend/app/services/dashboard.py` and `apps/backend/app/api_models.py` resolve
  presentation metadata from the fixed `TEAM_BY_ID` map.
- `apps/backend/app/persistence/composition.py` selects memory or Mongo case
  repositories. Global administration data has no repository. Mongo currently stores
  one schema-v2 case envelope per case in `clm_case_snapshots` and uses revision CAS.
- `apps/backend/app/services/document_processing.py` and
  `apps/backend/app/services/ownership_analysis.py` receive policy thresholds once at
  application composition. The same process-wide values are read by reconciliation,
  CLM readiness, and zero-touch orchestration.
- `apps/frontend/src/pages/PolicyRules.tsx` is read-only. It calls
  `/api/system/execution-profile`; `apps/frontend/src/viewModels.ts` invents the page
  catalogue from execution-profile fields and truthful unavailable/pending labels.
- `apps/frontend/src/App.tsx` is a 2,234-line hotspot with six unconditional workspace
  tabs. It gives Director case-creation options from `profile.available_teams`.
- `apps/frontend/src/pages/CaseQueue.tsx` and
  `apps/frontend/src/pages/OnboardedClients.tsx` call the same case-list API;
  `apps/frontend/src/pages/Dashboard.tsx` calls its own aggregate API. None has a team
  selector.
- `apps/frontend/src/types.ts` hard-codes both team IDs and the three roles.
- Phase 13 accepted evidence confirms generic login failure, opaque process-local
  sessions, one-session rotation, safe cookies, session-bound CSRF, exact browser-origin
  handling, cross-team non-enumeration, backend-authored team creation, memory test
  isolation, and generated physical Mongo databases. These controls are preservation
  requirements, not redesign opportunities.

DBS/OCBC classification from the full hidden-file-aware repository search:

| Classification | Current locations | Phase 14.5 disposition |
|---|---|---|
| Canonical persisted identifier | No case stores DBS/OCBC; cases store `TEAM_A`/`TEAM_B` | Preserve IDs; no case migration |
| Live user-facing metadata | `domain/access.py`; current backend/frontend auth, Dashboard, priority, and UI tests | Replace with exact `Alpha` / `Beta` metadata |
| Current documentation | project context, Phase 13 architecture, access contract, decision log D-035, demo runbook | Update current-state wording; append a new decision rather than rewriting D-035 |
| Historical evidence | Phase 13 planner and all Phase 13 execution/quality reports | Preserve verbatim as historical records |
| Stale test fixtures | Phase 13 backend/frontend tests containing DBS/OCBC labels | Update expected live presentation while retaining `TEAM_A`/`TEAM_B` assertions |

## 3. Phase 14.5 goals

1. Preserve existing case-team identifiers while renaming current presentation to
   Alpha/Beta.
2. Replace fixed team/profile runtime authority with repository-backed typed owners.
3. Add dynamic team creation and profile assignment without access inheritance.
4. Add HR as a separate identity/team administrator with no client-case access.
5. Keep passwords hashed with the accepted scrypt format and revoke stale sessions
   after authority changes.
6. Add a typed global policy catalogue with view, create, edit, per-rule reset, and
   whole-catalogue reset.
7. Make only existing bounded business rules runtime-active and truthfully label every
   other rule.
8. Add a backend-authoritative Director filter across Cases, Dashboard, and Onboarded.
9. Provide memory/Mongo parity, CAS conflict behavior, immutable bounded audit evidence,
   and isolated physical tests.
10. Keep the feature delta separable from concurrent Phase 14 until that work reaches
    `origin/main`.

## 4. Explicit non-goals

- No Phase 14 hard-delete or query-cache work, pagination, case reassignment, case/team
  migration, team deletion, user deletion, self-service signup, invitations, email,
  MFA, SSO/PingFederate, JWT, or distributed session store.
- No password reset/change flow after profile creation and no account disable/reactivate
  flow. These require separate lifecycle and recovery decisions.
- No team deactivation in the UI/API. `active` is stored and seeded `true` as a forward
  compatibility field, but remains system-owned in this phase.
- No Director identity/team administration and no HR policy mutation.
- No arbitrary policy JSON, formulas, scripts, expression languages, or executable code.
- No retroactive recomputation of current/completed cases after policy edits.
- No new runtime policy for scheduler, risk, screening, Ready-for-Approval, source
  precedence, approval authority, or production compliance.
- No separate database and no mutation of shared `clm_poc` during tests.
- No changes to ACRA, GoldTier, IDP provider contracts, UBO graph calculation, or
  unrelated workflow behavior beyond reading the two bound policy values.

## 5. Role/capability matrix

The backend owns this matrix. The auth response may expose a safe list of capabilities
for UI rendering, but the server rechecks every route.

| Capability | Client Onboarder | Relationship Manager | Director | HR |
|---|---:|---:|---:|---:|
| Sign in / own profile | Yes | Yes | Yes | Yes |
| View policy catalogue | Yes | Yes | Yes | Yes |
| Create/edit/reset policy | No | Yes | Yes | No |
| View own-team cases | Yes | Yes | Global | No |
| Use existing case mutations | Own team | Own team | Global | No |
| Create case | Own team, server assigned | Own team, server assigned | Explicit active team | No |
| Filter case portfolio by team | No | No | Yes | No |
| List/create/update profiles | No | No | No | Yes |
| List/create/update teams | No | No | No | Yes |
| Assign roles/teams | No | No | No | Yes |

Canonical capability values should be a closed enum such as `POLICY_VIEW`,
`POLICY_MUTATE`, `CASE_ACCESS`, `CASE_GLOBAL`, `IDENTITY_ADMIN`, and `TEAM_ADMIN`.
Role-to-capability mapping lives in one backend module. The frontend never submits a
capability and never treats its rendered list as authorization.

## 6. Alpha/Beta compatibility design

- Preserve exact IDs `TEAM_A` and `TEAM_B` in all existing/new case ownership fields.
- Seed team records as:

  - `TEAM_A`: display name `Alpha`; client/coverage label `Alpha`; team type
    `Corporate Client Onboarding`.
  - `TEAM_B`: display name `Beta`; client/coverage label `Beta`; team type
    `Corporate Client Onboarding`.

- Existing Maya/Ethan records keep `TEAM_A`; Sophia/Ryan keep `TEAM_B`; Olivia remains
  teamless/global.
- Remove `TEAMS`/`TEAM_BY_ID` as runtime presentation/authorization owners after all
  consumers use `TeamRepository`/`TeamDirectoryService`. Retain only immutable seed
  definitions for `TEAM_A` and `TEAM_B` in the administration bootstrap module.
- Do not rewrite case envelopes, seeder case ownership, historical reports, or Phase 13
  evidence solely for the rename.
- Current-state documentation and live tests change to Alpha/Beta. D-035 remains
  historical; add a Phase 14.5 decision that supersedes only its presentation mapping.

## 7. Dynamic `TeamId` strategy

Replace the `StrEnum` with a strict string value object/annotated type validated by one
backend adapter:

`^(TEAM_A|TEAM_B|TEAM_[A-F0-9]{24})$`

New IDs are generated server-side as `TEAM_` plus 12 cryptographically random bytes in
uppercase hexadecimal. Generation retries a bounded number of times on a unique-key
collision and otherwise fails with a safe 503. Display names are never IDs.

The frontend type becomes an opaque string alias, not a union of known teams. Browser
values are accepted only where a route permits a team selection, then validated for
syntax, repository existence, and `active=true`. HR team creation has no `team_id`
request field. Existing cases with null team remain legacy/unassigned and are not teams.

## 8. Team persistence model

`TeamRecord` is a frozen/strict typed model containing:

- `team_id: TeamId`;
- `display_name` (trimmed, 2–80 characters);
- `normalized_display_name` (backend-derived Unicode-normalized, trimmed, collapsed
  whitespace, case-folded key; never accepted from the client);
- `team_type` (fixed to `Corporate Client Onboarding` in this phase);
- `client_scope_label` (trimmed, 2–80 characters);
- optional `description` (maximum 240 characters);
- `active: bool` (always `true` and not mutable in Phase 14.5);
- `version: int`;
- `created_at`, `updated_at`, `created_by`, `updated_by`;
- append-only bounded `audit_events` with no secret fields.

`TEAM_A`/`TEAM_B` are bootstrap records. Team metadata updates never touch case
`team_id`. Duplicate normalized display names and coverage labels are rejected with a
safe 409. New teams receive no cases and no implicit relationship to Alpha/Beta.

## 9. User/profile persistence model

Separate browser-safe `UserProfile` from internal `UserAccountRecord`. The account
record contains:

- immutable normalized `user_id` matching `^[a-z][a-z0-9-]{2,31}$`;
- `display_name` (trimmed, 2–80 characters);
- closed `role` including new `HR`;
- nullable `team_id`;
- `credential_hash` in the existing fixed scrypt encoding, excluded from repr/API;
- `security_version` incremented on role/team/credential authority changes;
- optimistic `version`;
- `created_at`, `updated_at`, `created_by`, `updated_by`;
- append-only audit entries whose before/after projections exclude credential hashes.

Validation is repository-independent: Relationship Manager and Client Onboarder require
an existing active team; Director and HR require `team_id=null`. `user_id` is immutable.
There is no plaintext-password field on the stored model and no API response type can
represent `credential_hash`.

HR may create another HR. An HR cannot change its own role. Demoting an HR is rejected
if it would leave no HR record. These checks are server-side and occur under the profile
repository mutation lock/CAS boundary.

## 10. Credential storage and hashing design

- Reuse `generate_scrypt_password_hash`, `parse_scrypt_password_hash`, fixed scrypt
  parameters, dummy-hash unknown-user behavior, and constant-time digest comparison.
- Profile creation accepts a masked password of 12–128 characters. The frontend
  confirms it locally and submits the password once; confirmation is not stored or
  returned. The backend independently validates bounds and hashes immediately.
- Persist only the encoded scrypt hash in the profile collection. Do not log, return,
  audit, interpolate into errors, or retain the plaintext.
- Authentication loads the internal account by normalized user ID, uses the dummy hash
  for unknown/malformed users, and returns the same fixed 401 for every credential
  failure.
- No hash export/list endpoint exists. Safe profile responses contain only identifiers,
  display name, role, team metadata, version, and timestamps.

## 11. HR bootstrap design

Use one exact synthetic POC-only identity:

- user ID: `hr-admin`;
- display name: `POC HR Administrator`;
- role: `HR`;
- team: null;
- credential setting: `PHASE14_5_HR_ADMIN_PASSWORD_HASH`;
- credential format: the same accepted scrypt encoding as Phase 13.

The hash generator must request the HR password through hidden input and emit only the
encoded hash. No default password, hint, reusable test password, or plaintext appears in
tracked files or logs.

Bootstrap is idempotent and fail-closed. It validates existing records, inserts missing
seed records without overwriting any persisted hash/profile/team, and refuses startup
when a required missing seed lacks a valid environment hash. Partial bootstrap can be
resumed safely on the next start because inserts are unique and existing valid records
are preserved.

## 12. Existing synthetic-profile migration

Seed the accepted records exactly:

| User ID | Display name | Role | Team |
|---|---|---|---|
| `maya-lim` | Maya Lim | `CLIENT_ONBOARDER` | `TEAM_A` |
| `ethan-tan` | Ethan Tan | `RELATIONSHIP_MANAGER` | `TEAM_A` |
| `sophia-ng` | Sophia Ng | `CLIENT_ONBOARDER` | `TEAM_B` |
| `ryan-lee` | Ryan Lee | `RELATIONSHIP_MANAGER` | `TEAM_B` |
| `olivia-koh` | Olivia Koh | `DIRECTOR` | null |

Memory mode seeds all six accounts and two teams on every process start and therefore
requires all six valid environment hashes each time. Mongo mode uses the five existing
Phase 13 settings plus the new HR setting only to insert missing seed accounts. Once a
valid account exists in Mongo, its persisted hash is authoritative and the corresponding
environment value may be removed; startup must not overwrite it. An invalid persisted
record fails closed instead of being repaired from environment configuration.

Rename `scripts/generate_phase13_demo_password_hashes.py` to the accurate internal
owner `scripts/generate_admin_bootstrap_password_hashes.py` and update current callers
and documentation. This is code-retirement, not a compatibility alias: repository
search shows only internal tracked consumers. Historical reports retain the old name.

## 13. Session revocation design

Keep opaque process-local server sessions and one active session per user; do not add
JWT. Change `SessionRecord` to store `user_id` and the account `security_version`, not an
authoritative profile snapshot. On every authenticated request:

1. Validate token shape/digest/expiry.
2. Load the current account from `ProfileRepository`.
3. Reject and remove the session if the account is missing or its `security_version`
   differs.
4. Construct the request actor from the current safe profile and current team metadata.

After a successful HR role/team CAS update, increment `security_version` and call
`AuthenticationService.revoke_user_sessions(user_id)`. The version check is the
fail-safe if explicit process-local revocation races or fails after persistence. After
the HR response returns, the affected old cookie must receive fixed 401 on its next
request; a new login receives the new authority.

Replace `MAX_ACTIVE_SESSIONS = len(fixed_profiles)` with a bounded configuration
`phase14_5_max_active_sessions` (default 256, permitted 1–1000). Purge expired entries
before capacity checks and preserve atomic one-session rotation.

## 14. HR API contract

All routes are authenticated, centrally CSRF/origin protected when unsafe, and listed
in the exact route inventory. Router-level capability checks enforce `IDENTITY_ADMIN`
or `TEAM_ADMIN`; navigation hiding is not authority.

Error rules:

- unauthenticated: fixed `401 AUTHENTICATION_REQUIRED`;
- authenticated non-HR: fixed `403 ADMINISTRATION_FORBIDDEN`;
- stale version/normalized uniqueness collision: safe `409`;
- malformed input/role-team combination: safe `422` without echoing password/input;
- persistence unavailable: safe `503 ADMINISTRATION_UNAVAILABLE`.

The admin API never returns credentials, session digests, CSRF values beyond the
existing auth response, storage details, raw exceptions, or full audit internals.

## 15. Team-management API contract

| Method/path | Authority | Request | Response/behavior |
|---|---|---|---|
| `GET /api/teams/options` | Any authenticated role | none | Director/HR receive all active teams; team actors receive their current team only |
| `GET /api/admin/teams` | HR | none | Bounded admin metadata for all team records |
| `POST /api/admin/teams` | HR | display name, coverage label, optional description | Backend generates ID; `201`; no case migration |
| `PATCH /api/admin/teams/{team_id}` | HR | `expected_version` plus allowed metadata fields | CAS update; ID/type/active immutable |

`GET /api/teams/options` is the one selector source for Director filters and creation,
HR profile assignment, and any backend-authored active-team selector. It replaces
`available_teams` as a session snapshot. The auth profile still includes current team
metadata for account display, resolved fresh by the backend.

## 16. Profile-management API contract

| Method/path | Authority | Request | Response/behavior |
|---|---|---|---|
| `GET /api/admin/profiles` | HR | none | Safe bounded profile metadata only |
| `POST /api/admin/profiles` | HR | user ID, display name, role, nullable team ID, initial password | Validates role/team, hashes password, inserts audit-safe record |
| `PATCH /api/admin/profiles/{user_id}` | HR | `expected_version`, display name and/or role/team | User ID/hash immutable; CAS; authority changes revoke sessions |

The backend ignores no unknown fields; Pydantic `extra="forbid"` rejects mass
assignment such as `credential_hash`, `security_version`, `created_by`, capabilities,
or arbitrary team authority. Password change/reset, account disable, and deletion are
explicitly absent.

## 17. Policy-management API contract

| Method/path | Authority | Request | Response/behavior |
|---|---|---|---|
| `GET /api/policies` | All authenticated | none | Catalogue version plus safe typed rule summaries |
| `GET /api/policies/{policy_id}` | All authenticated | none | Current/default value, bounds, enforcement/classification, version, update metadata |
| `POST /api/policies` | RM, Director | expected catalogue version, category/name/description/value/value type | Creates only a bounded display/showcase rule; default equals initial value |
| `PATCH /api/policies/{policy_id}` | RM, Director | expected catalogue and rule versions plus allowed fields/value | Typed CAS update; system metadata and enforcement cannot be self-asserted |
| `POST /api/policies/{policy_id}/reset` | RM, Director | expected versions plus literal confirmation `RESET_POLICY_DEFAULT` | Restores that rule's default and audits the reset |
| `POST /api/policies/reset` | RM, Director | expected catalogue version plus literal confirmation `RESET_ALL_POLICY_DEFAULTS` | Atomically resets every rule without deleting the catalogue/custom rules |

Client Onboarder and HR receive fixed `403 POLICY_MUTATION_FORBIDDEN` on every mutation.
Unknown/unsupported values receive safe 422. Version conflicts receive
`409 POLICY_VERSION_CONFLICT`. The browser may never choose enforcement status for a
new rule or turn a showcase rule into a runtime rule.

## 18. Policy default catalogue

Persist one bounded typed catalogue (maximum 64 rules). Use separate classification and
enforcement axes: `PROJECT_DEFAULT`, `PENDING_SPONSOR_CONFIRMATION`, `SYSTEM_DERIVED`,
`DISPLAY_ONLY_NOT_RUNTIME_ENFORCED`; and `RUNTIME_ENFORCED`,
`DISPLAY_SHOWCASE_ONLY`, `NOT_EDITABLE`.

| Policy ID | Value/default | Type/bounds | Classification | Enforcement/editability |
|---|---|---|---|---|
| `DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD` | `0.85` | decimal string, 0–1, max 6 dp | Project default + pending sponsor Q-014 | Runtime-enforced; value editable |
| `OWNERSHIP_UBO_THRESHOLD_PERCENT` | `25.000000` | decimal string, 0–100, max 6 dp | Project default + pending sponsor Q-004 | Runtime-enforced; value editable |
| `OWNERSHIP_UBO_COMPARATOR` | `GREATER_THAN_OR_EQUAL_TO` | closed string | System-derived + pending sponsor Q-004 | Not editable |
| `REGISTRY_SUPPORTED_JURISDICTIONS` | `["SG"]` | bounded string list | System-derived | Not editable |
| `REGISTRY_PROVIDER` | `ACRA` | closed string | System-derived | Not editable |
| `DOCUMENT_SUPPORTED_MEDIA_TYPES` | PDF, DOCX, UTF-8 TXT | bounded string list | System-derived/project technical default | Not editable |
| `WORKFLOW_SUPPORTED_STAGES` | Registry, Document, Ownership, Readiness, Mock GoldTier, Complete | bounded string list | System-derived | Not editable |
| `RECONCILIATION_SOURCE_PRECEDENCE` | `NONE` | closed string | System-derived + pending sponsor Q-015 | Not editable |

Do not seed scheduler intervals, risk bands, reviewer counts, screening auto-clear, or
registry staleness values because the current application has no authoritative values.
The UI may retain clearly separated informational rows saying those capabilities are
unavailable; they are not persisted editable policies.

Every policy record contains `policy_id`, category, name, description, typed current
value, value type, default value, validation bounds/allowed values, classification,
enforcement, `version`, timestamps, and updater. Values use a strict discriminated
union for boolean, integer, decimal string, bounded string, and bounded string list.
There is no expression/code type.

## 19. Runtime-enforced versus showcase classification

Only the two existing thresholds are runtime-enforced:

- IDP confidence threshold: document semantic assessment, zero-touch low-confidence
  evidence, reconciliation confidence handling, and CLM readiness must resolve it from
  the case policy snapshot.
- UBO ownership threshold: ownership record creation and candidate classification must
  resolve it from the case policy snapshot; the existing inclusive comparator stays
  fixed and explicit.

System/derived entries are not editable. User-created entries are always
`DISPLAY_SHOWCASE_ONLY`; the backend assigns that value and the UI visibly states that
changing it does not alter onboarding. No orchestration service is allowed to look up a
showcase rule.

## 20. Policy version, reset, snapshot, and audit model

Store the global catalogue as one Mongo document with a catalogue `version` and bounded
typed `rules`. This permits atomic per-rule edits, add, single reset, whole reset, and a
consistent snapshot read without a cross-document transaction. Each edit increments
the catalogue version and affected rule version, even when reset restores an already
defaulted value, so the explicit administrative action is auditable.

Add `CasePolicySnapshot` to `OnboardingCase` with:

- `catalogue_version`/stable snapshot label;
- bound IDP threshold;
- bound UBO threshold;
- fixed inclusive comparator;
- `bound_at` UTC timestamp.

The binding point is case creation, before registry processing. A policy update affects
only cases created after the successful CAS. Stage execution always uses the case
snapshot. New case envelopes use schema v3. Schema-v1/v2 reads receive an explicit
in-memory `LEGACY_PHASE13_DEFAULTS_V1` snapshot (`0.85`, `25.000000`, inclusive) and are
not rewritten by reads. A later legitimate mutation may persist the fully validated v3
representation, but never changes the bound values.

Audit entries are append-only inside the authoritative team/profile/catalogue record so
the mutation and its evidence share one CAS without Mongo transactions (CI uses a
standalone Mongo service). Each entry contains event ID, closed action, actor user ID,
target ID, timestamp, resulting version, and bounded before/after metadata. Credential
hashes/passwords are impossible in the audit projection. The bounded POC limit is 256
entries per record; when full, further mutation fails closed rather than deleting old
audit evidence.

## 21. Director team-filter design

Decision: **INCLUDE Cases + Dashboard + Onboarded**. These are three presentations of
the authorized portfolio; filtering only Cases would create contradictory counts and
client lists.

Use one query contract on both case list and Dashboard:

- `team_filter=all` (Director default);
- `team_filter=unassigned` (legacy null-team cases);
- `team_filter=<canonical TeamId>`.

`CaseQueryService` applies actor authorization first, then validates/applies the Director
filter, then status/priority filters and ordering. Director may select any existing team
(active teams are offered; inactive historical IDs remain filterable only if a future
deactivation phase defines that behavior). Team actors must omit `team_filter`; any
attempt returns fixed 403 rather than accepting a client-authoritative override. HR
receives case-access 403. Dashboard consumes the same filtered `CaseQueryService`
records. Onboarded sends the same team filter with `status=COMPLETED`.

The selector options always come from `GET /api/teams/options`, so Team Gamma appears
without a frontend release. Selecting Gamma returns an empty portfolio until a Gamma
case exists.

## 22. HR zero-case-access design

Enforce zero access at both layers:

- Add explicit HR denial in `CaseAccessPolicy`; never rely on `team_id=None` falling
  through.
- Actor-only case list and Dashboard routes call a `CASE_ACCESS` capability guard and
  return fixed 403 to HR.
- Case creation calls the same guard before team resolution and returns fixed 403.
- Case-scoped direct-ID routes retain fixed `404 CASE_NOT_FOUND` for HR to avoid case
  enumeration.
- Existing case mutations cannot run because middleware does not attach an authorized
  case for HR.
- HR frontend navigation contains Policy, Administration/Users, Administration/Teams,
  and Account only. It does not mount/fetch Dashboard, New Onboarding, Cases, Onboarded,
  or Audit. Its default screen is Users.

## 23. Frontend navigation and screens

- Make workspace tabs capability-driven from backend-authored capabilities. Keep one
  central navigation definition; do not scatter role comparisons.
- `PolicyRules` loads `/api/policies`, shows current/default value, classification,
  enforcement truth, version, and updater. RM/Director see add/edit/reset controls;
  Client Onboarder/HR see the same catalogue read-only.
- Add `Administration > Users` for safe list, create form, and role/team edits. Initial
  password and confirmation are masked, cleared after submit, never repopulated, and
  never rendered in a success payload.
- Add `Administration > Teams` for list, create, and metadata edit. Do not add delete or
  deactivate controls.
- Add one reusable Director team-filter control to Cases, Dashboard, and Onboarded. Its
  state is view-local; every fetch includes the selected server-understood value.
- Director new-case selection uses fresh team options from the same endpoint, not the
  login snapshot.
- On any 401, preserve the accepted global transport behavior: clear the shell and
  return to login. On 409, refetch the affected admin resource and show a safe conflict.
- HR never sees an empty case shell; it lands directly in the administration workspace.

## 24. Mongo collections and indexes

Use the existing configured POC database, not a new database. Introduce:

1. Existing `clm_case_snapshots`: schema v3 for new writes; retain strict v1/v2 readers.
2. `clm_admin_teams`: `_id=team_id`; unique index on `normalized_display_name`; index on
   `(active, display_name)`.
3. `clm_admin_profiles`: `_id=user_id`; index on `(role, team_id)`; credential hash is
   stored but never indexed or projected.
4. `clm_admin_policies`: singleton `_id=GLOBAL_POLICY_CATALOGUE`; no secondary index
   required because all bounded rules are atomically owned by the single document.

Add explicit validated setting names for the three collection names with safe defaults.
`MongoAdminStore` shares the application Mongo client lifecycle but has its own
collections and repository interfaces. Startup pings/creates indexes/strictly validates
all admin records before serving requests. It never silently falls back to memory.

## 25. Memory-mode parity

Provide `InMemoryTeamRepository`, `InMemoryProfileRepository`, and
`InMemoryPolicyRepository` behind the same protocols as Mongo. Each returns defensive
copies, serializes mutations under `RLock`, enforces unique normalized names/IDs,
validates append-only audit prefixes, and uses identical CAS/version errors.

Ordinary tests continue to call `ordinary_test_settings()` with `_env_file=None`, forced
memory mode, and runtime-random hashes for all six seed identities. No ordinary test may
construct a Mongo admin store from inherited environment values.

Physical tests extend `scripts/mongo_test_safety.py` to allow only generated
`clm_p145_<24 hex>` databases. They use the existing test-only Mongo URI input, create
all four collections in that isolated database, close clients, drop only that exact
allowlisted database, retry cleanup, verify absence, and never inspect or mutate
`clm_poc`.

## 26. Concurrency/CAS/version strategy

- Team/profile updates require `expected_version`; Mongo filters on `_id` and version,
  memory checks under its lock, and stale writes fail 409.
- User/team uniqueness relies on canonical normalization plus unique indexes and matching
  memory checks.
- Policy operations require expected catalogue version; rule mutation also requires
  expected rule version. The single catalogue replacement is atomic and whole reset
  cannot expose a partially reset set.
- Bootstrap uses insert-if-absent semantics and never overwrites a current record.
- Role/team mutation commits the account/security-version CAS before revocation. The
  next authentication always reloads the account/version, so stale authority fails
  closed even if the explicit session-map removal races.
- Case policy snapshot creation reads one immutable catalogue version, validates the two
  runtime rules together, and persists them in the initial case write.
- No last-write-wins admin update, browser-computed version, or retry with silently
  refreshed authority is allowed.

## 27. Security threat and adversarial matrix

| Threat | Control | Required adverse proof |
|---|---|---|
| Self-asserted role/capability | Actor from server session; capability map closed server-side | Send role/capability fields to every mutation; 422/403 and no change |
| Non-HR user administration | HR guard after authentication | RM/Director/Onboarder get identical 403 on profile/team mutations |
| HR gains Director access | Explicit case capability denial and no case nav | HR list/dashboard/create 403; direct case 404; no case fetch from UI |
| Forged team ID | Strict syntax + repository existence/active check | Unknown, malformed, Alpha-like, mixed-case IDs rejected |
| New team inherits cases | Exact immutable team-ID matching | Gamma user sees zero Alpha/Beta cases |
| Cross-team filter escalation | Director-only filter; authorization before filter | RM/Onboarder filter attempts 403 and reveal no counts/IDs |
| Stale role/team session | Security version check + explicit revocation | Old cookie 401 immediately after successful admin response |
| Password/hash leakage | Immediate scrypt; private model; allowlisted API/audit/log projection | Response/log/audit/raw non-secret inspection contains no plaintext/hash |
| User enumeration | Dummy hash and fixed login response | unknown ID and wrong password have same status/body/timing class |
| Mass assignment | Strict request DTOs with `extra=forbid` | hash, version, updater, active, capability, ID injection rejected |
| CSRF/origin bypass | Preserve Phase 13 central middleware | missing/wrong CSRF, foreign/duplicate Origin/Referer rejected on every new unsafe route |
| Policy value/code injection | Discriminated value union, bounds, no expression type | scripts, nested JSON, NaN/Infinity, bool-as-int, overlong/list overflow rejected |
| False runtime claim | Backend-owned enforcement enum and fixed runtime ID allowlist | showcase edit changes no workflow; UI labels it non-runtime |
| Retroactive policy change | Immutable creation snapshot | pre-edit case retains old threshold; post-edit case binds new threshold |
| Conflicting admin writes | Expected versions and atomic CAS | exactly one concurrent writer succeeds; loser receives 409 |
| Bootstrap takeover | Env hash only for missing exact seed; never overwrite | restart with changed env hash does not replace persisted account |
| HR self-lockout/last-HR loss | no self-role change; preserve at least one HR | self-demotion and last-HR demotion rejected |
| Audit tampering/secret inclusion | append-only prefix validation and safe projection | removal/reorder/change of old events rejected; no credential fields possible |
| Mongo test contamination | forced ordinary memory + allowlisted generated DB | hostile inherited `clm_poc` env still yields memory; cleanup verified |

Known bounded limitation: a request that completed authentication immediately before a
concurrent authority change may finish; after the HR update response, all subsequent
requests from the old session fail. Distributed immediate revocation is outside this
process-local POC.

## 28. Detailed test matrix

### Alpha/Beta and compatibility

- Assert repository seeds `TEAM_A -> Alpha` and `TEAM_B -> Beta`, with coverage labels
  Alpha/Beta and unchanged IDs.
- Assert every current auth, Dashboard, case list/detail, Director creation selector,
  demo runbook fixture, and profile view renders Alpha/Beta.
- Assert existing schema-v2 raw cases keep `TEAM_A`/`TEAM_B` after read and ordinary
  mutation; no bulk case migration exists.
- Assert existing Maya/Ethan and Sophia/Ryan logins retain exact team access.
- Assert historical Phase 13 reports are not modified by the implementation diff.

### Dynamic teams and Director filters

- HR creates Gamma; returned ID matches generated syntax and request cannot provide ID.
- Gamma appears in HR assignment, Director creation, Cases/Dashboard/Onboarded filters.
- Duplicate normalized `Gamma`, whitespace/case variants, invalid/overlong names, and
  forged audit/active/type fields fail.
- New Gamma user logs in and sees zero Alpha/Beta cases; Director still sees all.
- `all`, Alpha, Beta, Gamma, and unassigned filters return exact sets on case list,
  Dashboard totals/breakdowns/lists/trend, and Onboarded completed list.
- RM/Onboarder filter attempts fail 403; HR case APIs fail as section 22 specifies.
- Team metadata update changes presentation/options but not stored case IDs.

### Policy

- All four roles can list/get safe policy data.
- RM and Director can create showcase policies and edit/reset allowed rules.
- Onboarder and HR mutations return fixed 403; unauthenticated returns 401.
- Runtime, showcase, and not-editable classifications cannot be client-overridden.
- Each malformed type/bound, arbitrary object/code expression, NaN/Infinity,
  bool-as-integer, unknown field, excessive list/string, and immutable-field change is
  rejected without echo.
- Single reset and whole reset restore exact canonical defaults, retain custom rules,
  increment versions, and append safe audit events.
- Stale/concurrent updates yield one success and a fixed 409 conflict.
- A pre-update case retains `0.85`/`25`; a post-update case binds new values. Focused
  document and ownership scenarios prove the future behavior changes exactly at the
  threshold boundary.
- Showcase-only edits do not change document, ownership, reconciliation, CLM, or
  zero-touch output.
- Schema-v1/v2 cases resolve the fixed Phase 13 legacy policy snapshot without read
  rewrite.

### Profiles, credentials, roles, and sessions

- HR creates new RM/Alpha and Onboarder/Beta; normal login and exact team access work.
- HR creates profile/Gamma; login succeeds and authorized portfolio is empty.
- Duplicate/case-variant user ID, unknown team, malformed role/team combinations,
  Director/HR with team, and team roles without team fail.
- Non-HR create/update returns fixed 403.
- Plaintext password and hash are absent from responses, errors, audit events, normal
  logs, repr snapshots, and frontend retained state after success.
- Persisted hash validates through normal login; bad/unknown login stays
  non-disclosing.
- HR changes RM Alpha to Beta: old session is revoked; new login sees Beta only.
- HR changes team user to Director: team becomes null; old session fails; global access
  appears only after login.
- HR remains no-case-access after login and after other profile changes.
- Self-demotion and last-HR demotion fail; bounded creation of a second HR succeeds.
- Dynamic session capacity proves more than five profiles can hold sessions up to the
  configured bound; overflow safely returns 503; per-user rotation stays atomic.

### Mongo and isolation

- Use only a generated `clm_p145_*` database and verify the name guard before any
  create/drop.
- Teams, profiles/hashes, policy catalogue/versions/audit, and new case snapshots
  survive application restart.
- Changed environment hashes after bootstrap do not overwrite Mongo credentials.
- Gamma remains case-empty; Alpha/Beta case IDs remain compatible.
- v1/v2/v3 strict decode, unknown versions/fields, identity mismatch, malformed admin
  records, and tampered audit prefix fail closed.
- Ordinary hostile-environment tests prove inherited Mongo settings cannot select the
  shared database.
- Physical cleanup retries, verifies absence, redacts driver detail, and records that
  shared `clm_poc` was untouched.

### Existing regression/security

- Re-run the full Phase 13 auth/RBAC, priority, Dashboard, test-isolation, Mongo safety,
  demo seeder, contract, frontend, and Windows lifecycle suites.
- Re-run duplicate Origin/Referer cardinality, production canonical origin, cookie,
  CSRF, route inventory, direct-ID 404, provider-free reads, and secret checks.
- Confirm no new route is public and every unsafe route is centrally protected.

## 29. Expected files and modules

Exact final paths may be reconciled with newer Phase 14 main, but the ownership boundary
must remain. Expected implementation surface:

**Create — backend owners**

- `apps/backend/app/domain/administration.py`
- `apps/backend/app/domain/policy.py`
- `apps/backend/app/services/admin_repository.py`
- `apps/backend/app/services/administration.py`
- `apps/backend/app/services/policy_management.py`
- `apps/backend/app/persistence/mongo_admin_store.py`
- `apps/backend/app/api_admin.py`
- `apps/backend/app/api_policies.py`

**Modify — backend integration/runtime binding**

- `apps/backend/app/domain/access.py`
- `apps/backend/app/domain/models.py`
- `apps/backend/app/domain/dashboard.py`
- `apps/backend/app/services/authentication.py`
- `apps/backend/app/services/authorization.py`
- `apps/backend/app/services/case_query.py`
- `apps/backend/app/services/dashboard.py`
- `apps/backend/app/services/document_processing.py`
- `apps/backend/app/services/ownership_analysis.py`
- `apps/backend/app/services/reconciliation.py`
- `apps/backend/app/services/clm_orchestration.py`
- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/app/persistence/models.py`
- `apps/backend/app/persistence/mongo_case_store.py`
- `apps/backend/app/persistence/repositories.py`
- `apps/backend/app/persistence/composition.py`
- `apps/backend/app/api_auth.py`
- `apps/backend/app/api_models.py`
- `apps/backend/app/config.py`
- `apps/backend/app/composition.py`
- `apps/backend/app/main.py` (router/composition wiring only)

**Create/modify — backend tests and scripts**

- `apps/backend/tests/test_phase14_5_administration.py`
- `apps/backend/tests/test_phase14_5_policy.py`
- `apps/backend/tests/test_phase14_5_case_access.py`
- `apps/backend/tests/test_phase14_5_real_mongo.py`
- `apps/backend/tests/test_phase14_5_test_isolation.py`
- `apps/backend/tests/phase13_test_credentials.py`
- `apps/backend/tests/phase13_test_settings.py`
- `apps/backend/tests/test_phase13_auth_rbac.py`
- `apps/backend/tests/test_phase13_dashboard.py`
- `apps/backend/tests/test_phase13_priority.py`
- `apps/backend/tests/test_phase13_real_mongo.py`
- `scripts/mongo_test_safety.py`
- rename `scripts/generate_phase13_demo_password_hashes.py` to
  `scripts/generate_admin_bootstrap_password_hashes.py`
- `scripts/seed_phase13_demo.py`
- `scripts/validate_phase13_mongo_dashboard.py`
- `tests/contract/phase13_contract_credentials.py`
- `.github/workflows/ci.yml` (add the Phase 14.5 physical test to the existing Mongo job;
  preserve all jobs)

**Create — frontend focused surfaces**

- `apps/frontend/src/pages/AdminUsers.tsx`
- `apps/frontend/src/pages/AdminTeams.tsx`
- `apps/frontend/src/pages/DirectorTeamFilter.tsx`
- `apps/frontend/src/Phase145AdminPolicy.test.tsx`

**Modify — frontend hotspots/consumers**

- `apps/frontend/src/types.ts`
- `apps/frontend/src/api.ts`
- `apps/frontend/src/auth.tsx`
- `apps/frontend/src/App.tsx` (imports, capability-driven tabs, focused page routing only)
- `apps/frontend/src/pages/PolicyRules.tsx`
- `apps/frontend/src/pages/CaseQueue.tsx`
- `apps/frontend/src/pages/Dashboard.tsx`
- `apps/frontend/src/pages/OnboardedClients.tsx`
- `apps/frontend/src/viewModels.ts`
- `apps/frontend/src/App.test.tsx`
- `apps/frontend/src/Phase13AuthPriority.test.tsx`
- `apps/frontend/src/Dashboard.test.tsx`
- `apps/frontend/src/UiV2Integration.test.tsx`
- `apps/frontend/src/design-system.css`

**Create/update — current documentation**

- `docs/architecture/PHASE_14_5_POLICY_TEAM_IDENTITY_ADMIN.md`
- `docs/contracts/POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md`
- `docs/decisions/DECISION_LOG.md`
- `docs/sponsor-questions/OPEN_QUESTIONS.md` (clarify provisional Phase 14.5 behavior;
  do not close sponsor questions)
- `docs/demo/DEMO_RUNBOOK.md`
- `docs/integration/CONFIGURATION_REFERENCE.md`

No dependency or lockfile change is expected.

## 30. Implementation slices and order

### Slice 1 — Administration domain and persistence foundation

**Files:** new administration/policy domain, repository protocols, memory repositories,
Mongo admin store; config/persistence composition; persistence-focused tests.

**Why:** teams, profiles, and policies need one non-case global authority before auth or
UI can safely become dynamic.

**Change necessity:** configuration/docs alone cannot create runtime identities or
global policy state. The minimum boundary is three repositories and one composition
bundle; storing this data in a case envelope is prohibited.

**Impact/compatibility:** seed `TEAM_A`/`TEAM_B`; do not alter case behavior yet.

**Steps:**

1. Add strict team/account/policy/audit models and normalization/value validators.
2. Add repository protocols and memory CAS implementations with defensive copies.
3. Add Mongo collections/indexes/CAS implementations using the existing client/database.
4. Add idempotent bootstrap seeds and fail-closed validation without overwriting records.
5. Add focused model, uniqueness, CAS, append-only audit, and hostile-input tests.

**Verification:** run the new administration/policy repository tests and existing
Phase 12/13 persistence tests.

### Slice 2 — Authentication migration, HR bootstrap, and revocation

**Files:** `domain/access.py`, authentication/config/composition/auth API, hash generator,
test/contract credential helpers, focused auth tests.

**Why:** HR-created profiles must authenticate from persistent hashes and authority
changes must invalidate old sessions.

**Change necessity:** the fixed tuple/hash map and actor session snapshot cannot support
runtime profiles or safe role/team mutation.

**Impact/compatibility:** preserve IDs, login response non-disclosure, cookie, CSRF,
Origin/Referer, one-session rotation, and process-local sessions.

**Steps:**

1. Generalize TeamId/Role and profile validation; add backend capability mapping.
2. Make AuthenticationService repository-backed with dummy-hash failure parity.
3. Store user/security version in sessions, reload current account per request, and add
   explicit user revocation.
4. Add `hr-admin` bootstrap setting and generalize session capacity.
5. Rename/generalize the hash generator and update current consumers.
6. Prove all six bootstrap logins, dynamic login, non-disclosure, rotation, capacity,
   and stale-session revocation.

**Verification:** focused Phase 14.5 auth tests plus full `test_phase13_auth_rbac.py`.

### Slice 3 — HR administration APIs and UI

**Files:** admin service/router, route inventory, main wiring, frontend API/types,
AdminUsers/AdminTeams, App navigation, tests.

**Why:** implement the owner-required HR workflow without granting case or policy power.

**Change necessity:** no current route or screen can create persistent profiles/teams.

**Impact/compatibility:** all unsafe requests retain central middleware; new router owns
admin DTOs instead of growing `main.py` handlers.

**Steps:**

1. Implement HR capability guards and safe error projection.
2. Implement team options/admin list/create/update with generated IDs.
3. Implement profile list/create/update with role/team validation, immediate hashing,
   last-HR safeguards, CAS, audit, and session revocation.
4. Add exact route inventory entries and include the focused router from `main.py`.
5. Implement capability-driven HR navigation and forms that clear password state.
6. Run the HR, mass-assignment, CSRF, forged-team, secret-projection, and UI tests.

**Verification:** Phase 14.5 admin/API/frontend focused suites and route inventory.

### Slice 4 — Alpha/Beta projection and dynamic Director filter

**Files:** team consumers in auth/API models/case query/Dashboard; case schema v3; three
frontend portfolio pages/filter component; current tests/docs/seeder.

**Why:** labels and Director filtering must be resolved from the dynamic canonical team
directory while keeping case ownership IDs stable.

**Change necessity:** fixed maps and fixed TypeScript union prevent new teams; local
frontend filtering cannot be authoritative.

**Impact/compatibility:** no case migration; authorization precedes filtering; provider-
free reads remain.

**Steps:**

1. Replace fixed runtime maps with TeamDirectoryService lookups in projections and
   Dashboard.
2. Introduce schema-v3 TeamId compatibility and strict v1/v2 reads.
3. Add the Director-only team filter to CaseQueryService, list API, and Dashboard API.
4. Reuse the filter in Cases, Dashboard, and Onboarded; use dynamic options in Director
   case creation.
5. Update live Alpha/Beta fixtures/current docs while preserving historical reports.
6. Prove Gamma empty access, Director all/team/unassigned results, team-user denial, and
   no provider calls.

**Verification:** Phase 14.5 case-access tests, existing priority/Dashboard/Mongo tests,
and frontend filter tests.

### Slice 5 — Policy catalogue API, reset, and audit

**Files:** policy service/router/main wiring, repository, frontend API/types,
PolicyRules, focused tests.

**Why:** provide truthful persistent policy administration with exact authority and
reset semantics.

**Change necessity:** the current page is a browser-derived read-only view and has no
global persistence or mutation owner.

**Impact/compatibility:** execution profile remains system/environment truth; it is no
longer the policy catalogue.

**Steps:**

1. Seed the exact eight-rule catalogue and strict typed validation metadata.
2. Implement authenticated reads and RM/Director-only CAS mutations.
3. Implement custom showcase creation and both confirmed reset operations.
4. Add safe audit/version/update metadata and fixed errors.
5. Replace browser-derived policy mapping with backend catalogue rendering and
   capability-driven controls.
6. Prove auth matrix, reset, conflict, injection rejection, and no false runtime claim.

**Verification:** policy backend/frontend tests and Phase 13 CSRF/route/security tests.

### Slice 6 — Per-case runtime policy binding

**Files:** case/domain persistence models; onboarding/document/ownership/reconciliation/
CLM/zero-touch services; tests and current policy docs.

**Why:** editable values must affect future behavior truthfully without changing
historical cases.

**Change necessity:** process-wide constructor thresholds would apply changes at restart
or unpredictably across in-flight cases; a case snapshot is the minimum stable owner.

**Impact/compatibility:** only two thresholds change source; max limits, comparator,
workflow policy constants, and existing records remain as defined.

**Steps:**

1. Add strict `CasePolicySnapshot` and fixed legacy Phase 13 snapshot.
2. Bind one catalogue version during initial case creation and persist it in schema v3.
3. Resolve document/reconciliation/CLM/zero-touch confidence decisions from the case
   snapshot.
4. Resolve ownership load/analysis threshold from the case snapshot/record.
5. Preserve existing CLM/zero-touch logic-version fields separately from admin policy
   catalogue version.
6. Prove pre/post-edit boundary behavior, restart durability, and no reinterpretation.

**Verification:** targeted threshold-boundary tests plus all document, ownership,
reconciliation, CLM, zero-touch, and Mongo regressions.

### Slice 7 — Broad security, Mongo, and merge-ready evidence

**Files:** physical/isolation tests, CI, current docs, execution report only as authorized
by the later execution prompt.

**Why:** close cross-boundary risk and prove no shared-data/security regression.

**Change necessity:** physical durability, test isolation, and broad regressions cannot
be inferred from unit tests.

**Impact/compatibility:** no shared `clm_poc` write; preserve every existing CI job.

**Steps:**

1. Run generated-database physical restart, persistence, hash-absence, Gamma-empty, and
   cleanup proofs.
2. Run the full adverse matrix and ordinary hostile-environment isolation.
3. Run all backend/frontend/contracts/lifecycle/static/secret checks in section 34.
4. Audit the diff for historical report preservation, no dependency/lockfile change,
   no secret, and no unrelated Phase 14 code.
5. After Phase 14 reaches main and merge authority is supplied, execute section 32 and
   rerun all affected/broad checks.

**Verification:** section 34 plus the post-merge drift/ancestry checks.

## 31. Phase 14 concurrent-merge conflict map

Highest-probability direct conflicts after Phase 14 reaches main:

- `apps/backend/app/main.py`: route/composition wiring and any new Phase 14 case routes.
- `apps/backend/app/services/authorization.py`: exact route inventory and case access.
- `apps/backend/app/services/case_query.py`: Phase 14 query/cache/filter work versus the
  Director team filter.
- `apps/backend/app/api_models.py`, `apps/backend/app/domain/models.py`: shared case API
  and domain fields.
- `apps/backend/app/persistence/models.py`, `mongo_case_store.py`, `repositories.py`,
  `composition.py`: Phase 14 hard-delete/cache/persistence composition versus schema v3
  and admin stores.
- `apps/backend/app/composition.py`: service dependency wiring.
- `apps/backend/tests/test_phase13_auth_rbac.py` and shared case/Mongo tests: route and
  persistence expectations.
- `apps/frontend/src/App.tsx`: navigation/routing and Phase 14 UI integration.
- `apps/frontend/src/api.ts`, `types.ts`: shared API/type contracts.
- `apps/frontend/src/pages/CaseQueue.tsx`, `Dashboard.tsx`, `OnboardedClients.tsx` and
  their tests: Phase 14 portfolio behavior versus team filters.

Lower-overlap focused modules should remain independently mergeable:
`domain/administration.py`, `domain/policy.py`, `admin_repository.py`,
`administration.py`, `policy_management.py`, `mongo_admin_store.py`, `api_admin.py`,
`api_policies.py`, `AdminUsers.tsx`, `AdminTeams.tsx`, and policy-focused tests.

## 32. Post-Phase-14 integration procedure

Do not inspect or copy the concurrent worktree. Do not integrate until Phase 14 is
accepted on `origin/main` and the user authorizes the merge.

1. Record the Phase 14.5 task state, current HEAD, index, tracked, and untracked files;
   ensure all Phase 14.5 implementation is reviewed/committed by the authorized owner.
2. Run `git fetch origin`.
3. Record `git rev-parse HEAD`, `git rev-parse origin/main`,
   `git merge-base HEAD origin/main`, and `git log --oneline HEAD..origin/main`.
4. Read the merged Phase 14 planner, architecture, execution/quality evidence, and
   changed hotspot files from `origin/main`; do not infer intent from conflict markers.
5. With explicit merge authority, run `git merge origin/main`. Never rebase.
6. For each conflict, preserve latest-main Phase 14 hard-delete/query/cache/security/API
   behavior, then reapply only the smallest Phase 14.5 admin/team/filter/policy delta.
   Never select whole-file ours/theirs.
7. Specifically reconcile case query order as: actor authorization -> optional
   Director team scope -> Phase 14 query/cache semantics -> status/priority ordering.
   Any cache key must include authenticated scope/team filter and cannot cache HR data.
8. Preserve Phase 14 case deletion boundaries: global admin teams/profiles/policies are
   never deleted by case hard-delete. A deleted case cannot remain visible through a
   cached Director/team portfolio.
9. Preserve both schema migrations/readers. If Phase 14 also increments the case schema,
   create one merged newest schema/read path rather than competing version constants.
10. Run focused tests for every conflict area, then the entire section 34 checklist.
11. Re-fetch, prove `HEAD..origin/main` empty, run `python scripts/pre_pr_check.py` only
    when the branch/index/worktree is clean and committed, and complete the repository
    pre-PR checklist.
12. Stop for owner review; do not push, open/merge a PR, or change branches without
    explicit instruction.

If Phase 14 changes any relevant contract so the ordering/cache/delete invariants above
cannot both hold, stop with the conflict unresolved and request an owner decision.

## 33. Sponsor and provisional assumptions

- Owner requirements in this Phase 14.5 prompt authorize the POC HR and policy matrix;
  they do not resolve production Q-016 or sponsor IAM/governance policy.
- Alpha/Beta are current POC presentation names only. `TEAM_A`/`TEAM_B` remain internal
  identifiers.
- The IDP `0.85` and UBO `25%` inclusive rules remain project defaults pending Q-014 and
  Q-004. Their editability is a POC administration capability, not sponsor approval.
- `NONE` source precedence remains the accepted conservative Q-015 boundary and is not
  editable.
- HR is separate, not senior to Director, and has no case/policy mutation authority.
- Storing scrypt hashes and process-local sessions remains synthetic POC security, not
  production identity management.
- No team/user deletion or deactivation is defined because referential, recovery, and
  last-administrator behavior would require a separate owner decision.
- No sponsor decision is needed to execute this bounded plan because all production
  claims remain excluded and provisional labels are explicit.

## 34. Quality-gate checklist

Run from the repository root unless the command changes directory explicitly. Never
load `.env` into ordinary tests; use existing runtime-random test credential helpers.

Focused checks after slices:

```powershell
python -m pytest apps/backend/tests/test_phase14_5_administration.py apps/backend/tests/test_phase14_5_policy.py apps/backend/tests/test_phase14_5_case_access.py apps/backend/tests/test_phase13_auth_rbac.py apps/backend/tests/test_phase13_dashboard.py apps/backend/tests/test_phase13_priority.py -p no:cacheprovider --tb=short
npm.cmd --prefix apps/frontend run typecheck
npm.cmd --prefix apps/frontend test -- --run
```

Runtime-policy regressions:

```powershell
python -m pytest apps/backend/tests/test_document_processing.py apps/backend/tests/test_ownership_analysis.py apps/backend/tests/test_reconciliation.py apps/backend/tests/test_clm_orchestration.py apps/backend/tests/test_zero_touch_orchestration.py -p no:cacheprovider --tb=short
```

Ordinary full/static checks:

```powershell
python -m pytest apps/backend/tests -p no:cacheprovider --tb=short
python -m ruff check apps/backend/app apps/backend/tests scripts
python -m ruff format --check apps/backend/app apps/backend/tests scripts
python -m mypy apps/backend/app
python -m pip check
npm.cmd --prefix apps/frontend run typecheck
npm.cmd --prefix apps/frontend test -- --run
npm.cmd --prefix apps/frontend run build
```

Contracts, lifecycle, security, and whitespace:

```powershell
$env:PYTHONPATH = "$PWD\apps\backend;$PWD\tests\contract;$PWD"
python -m unittest discover -s tests/contract -p "test_*.py"
python -m unittest discover -s tests -p "test_demo_lifecycle_windows.py" -v
python -m unittest discover -s tests -p "test_check_secrets.py"
python -m unittest discover -s tests -p "test_pre_pr_check.py"
python scripts/check_secrets.py
git diff --check
```

Physical Mongo is explicit opt-in only. Use the existing CI/test-only Mongo URI source,
but the test itself must generate and validate `clm_p145_*` before any write or cleanup:

```powershell
python -m pytest apps/backend/tests/test_phase14_5_real_mongo.py -p no:cacheprovider --tb=short
```

Before PR readiness, after authorized latest-main integration and a clean committed
tree:

```powershell
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
git merge-base HEAD origin/main
git log --oneline HEAD..origin/main
git status --short
python scripts/pre_pr_check.py
git diff --stat origin/main...HEAD
git diff --name-status origin/main...HEAD
git log --oneline origin/main..HEAD
```

Quality gate must fail if any required check is skipped/failed, any new route is absent
from the inventory, any ordinary test can select shared Mongo, any password/hash appears
in API/log/audit output, or `origin/main` remains ahead.

## 35. Exact execution-agent handoff

Use `$fyp-phase-execution`, `$integration-safe-development`, and
`$integration-security-review` against this planner after Phase 14.5 implementation is
explicitly authorized. Do not start from the concurrent Phase 14 worktree and do not
implement on `main`.

Execution agent instructions:

1. Re-verify branch, baseline, full working-tree/index state, and this planner before
   any write. Record a TaskStartSnapshot. If the branch or ownership state differs,
   stop rather than switching/resetting/stashing/cleaning.
2. Re-read current `origin/main` authority and determine whether Phase 14 has landed. If
   it has not landed, implement only isolated Phase 14.5 slices and do not inspect the
   other worktree. If it has landed, follow section 32 before PR readiness.
3. Implement slices 1–7 in order. Keep new domain/repository/router/page owners focused;
   do not expand `main.py` or `App.tsx` with business logic.
4. Preserve `TEAM_A`/`TEAM_B`, all five user IDs, central auth/CSRF/origin behavior,
   exact case-team matching, non-enumerating direct-ID 404, and no case-team mutation.
5. Treat `hr-admin`, Alpha/Beta mapping, policy authority, and legacy policy snapshot as
   synthetic/project decisions. Do not claim sponsor approval.
6. Never read or commit `.env`; never print passwords, hashes, sessions, CSRF values,
   Mongo connection detail, or confidential data. Never use shared `clm_poc` in tests.
7. Run focused checks after each slice and all section 34 checks after integration. Run
   the physical Mongo test only with explicit safe test connectivity and generated
   allowlisted database cleanup.
8. Update only current architecture/contracts/context/decision/open-question/demo/config
   documentation; preserve historical reports.
9. Report all API routes/models, TeamId/Role types, schema-v3, collection/config names,
   policy runtime binding, session behavior, and authorization changes explicitly.
10. Do not stage, commit, push, merge, rebase, reset, stash, clean, branch-switch, or
    start another phase unless the execution prompt separately authorizes that action.

### Planner architecture checks

**Aegis Visibility:** Planning is required because three fixed authorities are being
replaced across authentication, persistence, authorization, and historical behavior;
the key risk is parallel owners or retroactive policy/case authority.

**Plan Basis:** The requirement source is explicit and testable. No sponsor artefact is
needed because production policy remains provisional/out of scope.

**BaselineUsageDraft:**

- Required baseline refs: project rules/context, Phase 13 architecture/access contract,
  current code/tests, accepted Phase 13 final re-quality evidence, decision/open-question
  logs.
- Delivered context refs: owner Phase 14.5 request and repository `AGENTS.md`.
- Acknowledged before plan refs: all required refs above.
- Cited in plan refs: header and sections 2, 6, 12, 13, 18–22, 31–35.
- Missing refs: uncommitted concurrent Phase 14 work, intentionally prohibited.
- Decision: continue; Phase 14 merge behavior is fenced in section 32.

**Requirement Ready Check:**

- Requirement source refs: owner request supplied with this task.
- Goals/scope refs: owner feature groups A–F and deliverable sections.
- User/scenario refs: role/team/policy/profile/test matrices in the owner request.
- Requirement item refs: all 20 planner questions and 35 required deliverable areas.
- Acceptance refs: owner test/security matrices and final drift/safety checks.
- Open blocker questions: none for planning; sponsor production questions remain
  explicitly provisional and non-blocking.
- Decision: ready.

**Change Necessity:** A display-only rename cannot satisfy dynamic teams, persistent
credentials, backend policy mutations, or stale-session revocation. The minimum code
boundary is one global admin persistence bundle, repository-backed auth, server case
filtering, and two per-case runtime policy values. Decision: code-change.

**Existence Check:** Current case repositories cannot own global administration without
violating case lifecycle; fixed access tuples cannot safely generalize. Reuse the
existing persistence composition, auth middleware, case query, and service boundaries;
add only focused admin/policy domain/repositories/routers. Decision: add-with-proof.

**Architecture Integrity Lens:**

- Invariant: identity/team/policy authority is backend-authored and existing case
  decisions/ownership remain stable.
- Canonical owners: admin repositories for global state; case snapshot for runtime
  policy; CaseAccessPolicy/CaseQueryService for case scope.
- Responsibility overlap to retire: `TEAMS`, `TEAM_BY_ID`, fixed profile tuple as runtime
  authority, browser-derived policy catalogue, constructor-global mutable thresholds.
- Higher-level simplification: dynamic selectors and projections all consume one team
  directory; policy mutations and snapshots consume one catalogue.
- Retirement/falsifier: a remaining runtime lookup of the old fixed maps, or a service
  consulting live policy for an existing case, disproves completion.
- Verdict: proceed with focused owner split.

**Anti-Entropy/retirement decision:** Delete-first applies to internal fixed runtime
owners and the stale password-generator name after consumers migrate. Keep `TEAM_A`,
`TEAM_B`, schema-v1/v2 readers, existing user IDs/settings during seed migration, and
historical reports as proven compatibility boundaries. No persistent case/team/profile
data is deleted.

**Complexity Budget / Plan-Time Complexity Check:** `main.py` (1,790 lines) and
`App.tsx` (2,234 lines) are already over-pressure hotspots; `api_auth.py` (345),
`composition.py` (273), and persistence composition are at-risk. Put handlers, DTOs,
repositories, and screens in new focused modules; limit hotspots to imports/wiring/tab
routing. Split implementation by slices; do not perform unrelated refactors. Result:
at-risk but controlled by new owner files.

**Plan Pressure Test:** Owners and compatibility boundaries are explicit; verification
covers auth, persistence, runtime truth, UI, Mongo, and Phase 14 integration; every
slice names files, purpose, changes, impact, steps, and checks. Pressure result: proceed.

**Execution Readiness View:**

- Intent Lock: exactly the four owner feature groups plus necessary persistence/auth
  migration.
- Scope Fence: section 4 non-goals; no concurrent worktree access.
- Baseline Lock: accepted main SHA `aba264a...` until authorized post-Phase-14 merge.
- Approved Behavior: role matrix, Alpha/Beta, dynamic teams, policy CRUD/reset, Director
  filter, HR profile/team administration.
- Owner/Contract Constraints: backend authority, typed bounded values, central security,
  repository-backed global data, immutable case ownership/snapshots.
- Compatibility Boundary: header and sections 6, 12, 20, 31–32.
- Retirement Boundary: old fixed runtime maps and browser policy owner retire; persisted
  IDs/readers/history remain.
- Task Batches: slices 1–7.
- Test Obligations: sections 27, 28, 34.
- Review Gates: focused slice checks, security review, physical Mongo proof, independent
  quality gate, latest-main integration.
- Drift/Rewind Rules: no rebase/reset/whole-file conflict choice; stop on unreconcilable
  Phase 14 intent.
- Evidence Required Before Completion: green full matrix, clean scoped diff, no secrets,
  generated Mongo cleanup, empty main drift.
- Advisory Boundary: this planner is execution guidance, not completion or sponsor
  approval authority.

### Concrete answers to the 20 planner questions

1. Preserve `TEAM_A`/`TEAM_B` seed IDs; generate opaque IDs for new teams; authorize by
   exact stored ID.
2. Replace fixed `TeamId` enum with one constrained string/value-object type.
3. Store teams in a global `TeamRepository`, memory or `clm_admin_teams`.
4. Store users/hashes in a global `ProfileRepository`, memory or
   `clm_admin_profiles`.
5. Bootstrap exact synthetic `hr-admin` with `PHASE14_5_HR_ADMIN_PASSWORD_HASH`.
6. Idempotently seed the five accepted profiles with unchanged IDs/team IDs.
7. Use existing environment hashes only for missing seeds; persisted Mongo hashes become
   authoritative and are never overwritten.
8. Increment account security version, explicitly revoke user sessions, and reload/check
   account version on every request.
9. Yes; HR case portfolio/create APIs return 403, direct IDs return non-enumerating 404,
   and case UI/navigation is absent.
10. Runtime: IDP confidence and UBO threshold only. Custom rules are showcase-only;
    system/derived rules are not editable.
11. A runtime policy edit affects only cases created after the successful catalogue CAS.
12. Yes; persist an immutable per-case snapshot and synthesize a fixed legacy snapshot
    for schema v1/v2.
13. Provide confirmed single-rule and whole-catalogue reset, version increment, and
    append-only safe audit; never delete rules.
14. Include Cases, Dashboard, and Onboarded.
15. All selectors fetch `GET /api/teams/options` from the TeamRepository-backed service.
16. Add `clm_admin_teams`, `clm_admin_profiles`, `clm_admin_policies`; evolve
    `clm_case_snapshots` to schema v3.
17. Force ordinary memory settings with `_env_file=None`; physical tests use only
    generated allowlisted `clm_p145_*` databases and verified cleanup.
18. Team/profile version CAS; policy catalogue+rule CAS; unique normalized indexes;
    security-version session invalidation.
19. Exact likely hotspots are listed in section 31.
20. Wait for Phase 14 on main, fetch, merge `origin/main` when authorized, reconcile by
    intent, preserve both feature contracts, rerun focused then broad checks, never
    rebase.

**Execution Route:** inline coordinator with focused slice review checkpoints. The plan
has cross-slice dependencies (persistence -> auth -> APIs/UI -> runtime binding), so
parallel implementation would create avoidable shared-hotspot conflicts. If an execution
prompt explicitly requests subagents, delegate only read-only review or disjoint focused
modules after the owning interfaces are fixed. No user confirmation is required to use
this plan; implementation itself requires a separate explicit request.
