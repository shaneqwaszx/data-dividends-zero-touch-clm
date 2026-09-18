# Phase 13 — Case Prioritisation, Authentication & Team-Based RBAC

## Plan header

**Goal:** Add bounded POC authentication, five deterministic synthetic profiles, backend-enforced Team A/DBS and Team B/OCBC case visibility, Director global visibility, and durable optional case priority `1..10 | null` while preserving the accepted CLM workflow and UI V2.

**Architecture:** Authenticate each `/api` request through one server-side opaque-session boundary, derive a server-authored actor, authorize case access through one policy, store case `team_id` and `priority` on the canonical onboarding case inside the Phase 12 envelope, and build case lists through one backend query/ordering service.

**Tech stack:** Python 3.12, FastAPI 0.141.1, Pydantic 2, standard-library `hashlib.scrypt`/`secrets`/`hmac`, existing memory repositories, MongoDB 7/PyMongo, React 18, TypeScript 5.9, Vite 7, Vitest, pytest.

**Baseline/authority refs:** `AGENTS.md`; `docs/PROJECT_CONTEXT.md`; `docs/decisions/DECISION_LOG.md`; `docs/sponsor-questions/OPEN_QUESTIONS.md`; `docs/development/BRANCH_MERGE_PROTOCOL.md`; Phase 12 planner, architecture, recovery profile, execution/re-quality-gate reports; accepted UI V2 implementation/consolidated gate; zero-touch ordering reconciliation/parity gate; and the Phase 13 sponsor brief supplied for this planning task.

**Compatibility boundary:** Preserve Registry -> document -> reconciliation -> ownership -> CLM -> Mock GoldTier behavior, all current route paths, current response meaning, call stopping, replay prevention, UI V2 layout, and memory/Mongo parity. The intentional compatibility changes are mandatory authentication on protected APIs, additive case/profile/priority fields, Director-only visibility of legacy unassigned cases, and persistence schema version 2 with a controlled version-1 read migration.

**TDD Route:**

- Mode: off
- Decision: skipped
- Strict authority: not applicable
- Strict signals: authentication, authorization, IDOR safety, persistence migration, and shared API/type changes are high-risk, but neither the user nor project mandates strict RED/GREEN TDD.
- Light eligibility: not applicable because this is cross-module security and persistence work.
- TDD-fit exception: none.
- Test posture: implement each bounded owner with immediate focused post-change regression, then run adversarial and broad regression suites.
- Reason: project rules require meaningful tests, but do not prescribe strict test-first execution.
- Verification: focused auth/RBAC/priority tests, frontend tests, memory/Mongo parity and restart tests, full project CI-equivalent checks, security scan, POC regression, and independent Phase 13 Quality Gate.

**Verification:** Phase 13 is executable only when the focused, broad, security, genuine-Mongo CI, and independent quality-gate evidence listed in sections 20, 21, and 27 all pass.

## Planning controls

### Aegis visibility

Planning is necessary because this phase introduces a security owner, a public authentication contract, cross-route authorization, a persisted schema migration, and a new canonical ordering key that affect several existing consumers.

### BaselineUsageDraft

- Required baseline refs: all mandatory sources listed in the Phase 13 brief.
- Acknowledged before plan refs: all required refs, Phase 12 accepted persistence material, UI V2 accepted material, and the accepted ordering contract.
- Cited in plan refs: the plan header and sections 3, 4, 13, 14, 18, 24, and 27.
- Missing refs: none.
- Decision: continue.

### Requirement Ready Check

- Requirement source refs: the supplied Phase 13 sponsor brief and repository rules.
- Goals and scope refs: sponsor requirements 1–24 and explicit out-of-scope list.
- User/scenario refs: five profiles; Team A/DBS, Team B/OCBC, Director; priority `10, 8, 5, 1, null`; direct-ID and mutation attacks.
- Acceptance/verification refs: sponsor acceptance scenarios 18, POC regression catalogue, Phase 12 recovery profile, and CI workflow.
- Open blocker questions: sponsor production policy remains open, but the supplied project-defined POC rules are sufficient for this bounded implementation.
- Decision: ready.

### Change Necessity

- User-visible need: login, trusted profile context, team-isolated case data, Director visibility, and persistent priority ordering.
- No-change/non-code option: frontend filters or demo instructions cannot enforce authentication, prevent IDOR, or preserve priority through Mongo restart.
- Why code change is necessary: the backend currently has no identity, authorization, team ownership, priority model, session lifecycle, or protected route boundary.
- Minimum change boundary: focused auth/access/query modules plus narrow changes to canonical case data, persistence, application composition/routes, API projection, and the existing UI/API client.
- Decision: code-change.

### Existence Check

- Proposed new surfaces: authentication/session service, authorization policy, protected-route dependency/middleware, and case portfolio query service.
- Existing owner/reuse candidates: `OnboardingService`, `OnboardingCaseRepository`, zero-touch automation repository ordering, `main.py`, and frontend `api.ts`.
- Why existing surfaces are insufficient: none owns authenticated actors, session validation, access decisions, or the join of automation plus case metadata required for authorized priority ordering.
- Creation proof: new modules keep security logic out of the 1,673-line `main.py`, avoid duplicating the canonical case/persistence engines, and make route coverage testable.
- Entropy/retirement impact: POC session service is explicitly process-local and must be replaced by a production identity provider; case/team and priority domain fields remain valid beyond the demo auth mechanism.
- Decision: add-with-proof.

### Architecture Integrity Lens

- Invariant: no case data or mutation reaches an authenticated actor outside their server-authored team scope.
- Canonical owners/contracts: `OnboardingCase` owns case metadata; Phase 12 envelope owns durability; one access policy owns visibility; one query service owns list filtering and ordering; auth service owns sessions.
- Responsibility overlap: UI filters remain presentation-only and repositories remain identity-agnostic infrastructure; neither authorizes requests.
- Higher-level simplification: a global `/api` authentication boundary plus one reusable case-access dependency prevents per-handler authentication variants.
- Retirement/falsifier: a future production IAM phase replaces only the POC credential/session adapter while retaining `AuthenticatedActor` and policy contracts; discovery of an existing auth/access owner would require reuse instead.
- Verdict: proceed.

### Complexity Budget and Plan-Time Complexity Check

- Artifact class: security boundary, public API, canonical aggregate, persistence schema, and large frontend shell.
- Current pressure: `main.py` is 1,673 lines, `App.tsx` is 2,167 lines, `api.ts` is 401 lines, and persistence adapters already coordinate a shared envelope.
- Projected pressure: at-risk if auth and list policy are added directly to central files.
- Planned governance: add bounded auth/access/query modules and a login/auth context component; limit central files to composition, route wiring, and rendering integration.
- Recommendation: add owner files; edit `main.py`, `App.tsx`, `api.ts`, and shared types only at their existing composition boundaries.

### Plan Pressure Test

- Owner/contract/retirement: explicit for auth, policy, case metadata, query ordering, and POC session replacement.
- Architecture integrity/higher-level path: canonical case/envelope and existing automation tie-break are reused.
- Verification scope: route inventory, IDOR, CSRF/session lifecycle, migration, memory/Mongo parity, UI, and full regression are covered.
- Task executability: each implementation batch below identifies files, behavior, and exact checks.
- Pressure result: proceed.

## 1. Phase title and goal

Deliver a secure, bounded local POC in which users authenticate as one of exactly five synthetic profiles, case visibility is filtered by an explicit server-controlled `team_id`, and optional priority is validated, persisted, and sorted by the backend. This phase does not define production IAM or differentiated business permissions.

## 2. Sponsor requirements

- Priority is optional; only strict integers `1` through `10` or JSON `null` are valid. `10` ranks highest, `1` ranks above `null`, and equal priorities retain the accepted automation ordering.
- Team A is associated with the visible DBS scope; Team B with OCBC. The association is display metadata, never the authorization comparison.
- Team-scoped users see only cases whose stored `team_id` equals their authenticated team. Director sees Team A, Team B, and legacy unassigned cases.
- Role/team come only from the authenticated server-side profile. Client role/team headers, query strings, or frontend state have no authority.
- Login, authenticated session, current profile, logout, login UI, route protection, safe credential provisioning, and deterministic demo users/data are required.
- All existing case-addressable APIs, including demo APIs, must enforce the same case policy.
- Authentication and authorization fail closed and do not log password, hash, cookie, token, or authorization values.

## 3. Current architecture findings from main

The observed baseline is branch `phase/13-case-priority-auth-rbac` at `36d0247befce04bbed85e3dced9f9c1c2b617855`; local `origin/main` and the merge base are the same SHA.

- `OnboardingCase` in `apps/backend/app/domain/models.py` is the canonical case aggregate. It currently contains identifiers, jurisdiction/Registry state, Mock GoldTier result, events, and timestamps, but no team or priority.
- `OnboardingService` creates and mutates that aggregate through `OnboardingCaseRepository`. The memory repository owns defensive copies and a shared `RLock`; the Mongo adapter writes the onboarding portion of the Phase 12 envelope under envelope CAS.
- `DurableCaseSnapshot` in `apps/backend/app/persistence/models.py` is strict schema version 1. One Mongo document stores onboarding, documents, ownership, reconciliation, CLM, automation, target ledger, and demo scenario with a revision.
- `MongoCaseStore` validates every envelope and `_id`/`case_id` binding, updates envelope timestamps, and rejects unknown schema versions. Phase 12 intentionally has no general migration engine.
- The primary case list is `GET /api/clm/zero-touch/cases`. `main.py` joins `ZeroTouchAutomationRecord` with `OnboardingCase` and projects `ZeroTouchCaseListItemResponse`.
- The accepted case ordering is automation `updated_at` descending, then canonical string `case_id` descending for exact timestamp ties. Both memory and Mongo automation repositories call `order_zero_touch_automation_records`; Mongo envelope order is not the API order.
- The frontend is a React single-page shell without a routing library. `App.tsx` switches tabs in local state. It currently shows `OperatorAccount`/`AccountPlaceholder` text stating authentication is absent.
- `CaseQueue`, `OnboardedClients`, and `AuditTrail` call the same list endpoint. They fetch case details per listed ID. Their search/status/jurisdiction filters preserve received order and do not currently sort.
- `CasePortfolio` and `ReviewQueue` in `App.tsx` are retained test/demo components but are not mounted by the accepted active UI V2 route flow.
- `AuditTrail` is an event list, not a case-priority list. Its case discovery must be authorized; event rows should retain chronological workflow semantics rather than be sorted by case priority.
- The Vite development server proxies `/api` to FastAPI on the same browser origin. There is no CORS middleware and `api.ts` currently calls `fetch` directly.
- There is no current login, session store, actor, RBAC policy, CSRF control, security logger, or third-party authentication dependency.

## 4. Existing components/services/routes to reuse

Reuse rather than replace:

- `OnboardingCase`, `OnboardingService`, `OnboardingCaseRepository`, and the per-case lock as the metadata owner and atomic mutation boundary.
- `DurableCaseSnapshot`, `MongoCaseStore`, and Mongo repository adapters as the sole persistence engine.
- `ZeroTouchAutomationRepository.list_records()` and its accepted automation timestamp/case-ID ordering as the tie-break contract.
- `ZeroTouchOrchestrator`, `ClmOrchestrationService`, document/reconciliation/ownership services, demo controls, and target ledger without changing business rules.
- `ZeroTouchCaseSummaryResponse`, `ZeroTouchCaseListItemResponse`, and frontend `ZeroTouchCaseSummary`/`ZeroTouchCaseListItem` as additive projection surfaces.
- Vite `/api` proxy and same-origin browser deployment for cookie transport.
- UI V2 `WorkspaceTabs`, `CaseQueue`, `CaseDetail`, `OnboardedClients`, `AuditTrail`, view models, design-system CSS, and existing loading/error patterns.

No connector interface, GoldTier mapper, ACRA contract, UBO rule, document rule, or workflow status changes in Phase 13.

## 5. Proposed domain model

Create `apps/backend/app/domain/access.py` with strict frozen models/enums:

```text
TeamId = TEAM_A | TEAM_B
Role = CLIENT_ONBOARDER | RELATIONSHIP_MANAGER | DIRECTOR
Team { team_id, display_name, client_scope_label }
UserProfile { user_id, display_name, role, team_id? }
AuthenticatedActor { profile }
CasePriority = StrictInt constrained to 1..10
```

Add to `OnboardingCase`:

```text
team_id: TeamId | None = None
priority: CasePriority | None = None
```

`team_id` is assigned once during case creation and is immutable in repository updates. `priority` is mutable. Neither field is inferred from `legal_name`, UEN, visible client label, Registry payload, or request headers.

Exact profiles:

| user_id | display_name | role | team_id | visible client scope |
| --- | --- | --- | --- | --- |
| `team-a-onboarder` | Team A Client Onboarder | `CLIENT_ONBOARDER` | `TEAM_A` | DBS |
| `team-a-rm` | Team A Relationship Manager | `RELATIONSHIP_MANAGER` | `TEAM_A` | DBS |
| `team-b-onboarder` | Team B Client Onboarder | `CLIENT_ONBOARDER` | `TEAM_B` | OCBC |
| `team-b-rm` | Team B Relationship Manager | `RELATIONSHIP_MANAGER` | `TEAM_B` | OCBC |
| `director` | POC Director | `DIRECTOR` | `null` | All demo scopes |

These are role labels, not real employee identities.

## 6. Authentication design decision

Use an opaque session token in a host-only HTTP-only cookie with server-side validation. Do not use JWT and do not add an auth dependency.

- Generate session tokens with `secrets.token_urlsafe(32)` and store only a SHA-256 digest as the lookup key.
- Store actor, issue time, absolute expiry, and CSRF secret in a bounded process-local session repository.
- Verify password hashes using standard-library `hashlib.scrypt` and `hmac.compare_digest`; perform the same scrypt work for unknown users with a process-generated dummy hash.
- Protect every `/api` route through one middleware/global dependency except exact public endpoints `POST /api/auth/login` and `/health`. OpenAPI/docs expose schemas but no case data.
- `GET /api/auth/me`, `POST /api/auth/logout`, `/api/system/execution-profile`, demo discovery, and all case APIs require authentication.
- Return fixed safe `401` errors for missing, malformed, unknown, or expired sessions. Do not echo cookie values or parsing detail.

Cookie/CORS decision:

- Keep the accepted same-origin topology. Browser calls use `credentials: "include"`; Vite continues to proxy `/api`.
- Set `HttpOnly`, `SameSite=Strict`, host-only (no `Domain`), and `Path=/api`. Set `Secure=true` outside explicit loopback development/test; production configuration must fail startup if secure cookies are disabled.
- Do not add permissive CORS. A different frontend origin is unsupported in this phase. A future cross-origin deployment must add an explicit origin allowlist with credentials and re-review CSRF/cookie policy; wildcard origins are forbidden.
- Issue a random synchronizer CSRF token with login/current-profile responses. Keep it only in React memory and require it in `X-CSRF-Token` for authenticated unsafe methods. Validate it server-side with constant-time comparison and enforce same-origin `Origin`/`Referer` where present. Login is JSON-only and checks origin but is not session-authenticated.

## 7. Session lifecycle

1. Login accepts bounded `user_id` and password in JSON over the local POC HTTP boundary.
2. Auth service locates the fixed server profile and verifies the environment-provided scrypt hash.
3. Successful login revokes any existing session for that synthetic user, creates one opaque session with an eight-hour absolute TTL, sets the cookie, and returns profile plus CSRF token.
4. `/api/auth/me` validates cookie/digest/expiry and returns the same server-authored profile plus a CSRF token for page reload recovery.
5. Every protected request resolves the actor from the session. Expired sessions are removed and fail `401`.
6. Logout validates CSRF, deletes the server session first, and returns a response that expires the browser cookie.
7. Login rotation prevents fixation; cookie reuse after logout or replacement login fails.
8. Sessions do not survive backend restart. Existing cookies then fail `401`; the frontend clears local auth state and returns to login. This is an explicit POC limitation.
9. Keep one active session per synthetic profile, purge expired sessions on access/login, and fail closed if the bounded store cannot accept a session.

## 8. Demo credential provisioning approach

Keep the five profiles in source but all usable password material outside Git.

- Add five optional backend `SecretStr` settings, one scrypt hash per fixed `user_id`.
- When POC authentication is composed, require all five hashes to be present and structurally valid; missing/malformed hashes fail startup with a fixed message that names only the configuration key.
- Add `scripts/generate_phase13_demo_password_hashes.py`. It uses `getpass`, a cryptographically random salt, bounded scrypt parameters, and prints only environment assignment lines containing hashes. It never prints or persists plaintext.
- The operator copies hashes into the existing gitignored local `.env` or supplies them through the process environment. Do not add usable example hashes, default passwords, a credential file, or password values to docs/tests.
- Tests inject an auth service or create random runtime-only passwords/hashes; no stable test password is committed.

## 9. Team/RBAC policy

`CaseAccessPolicy.can_access(actor, case)` is the only visibility decision:

```text
DIRECTOR -> true for TEAM_A, TEAM_B, and null legacy cases
CLIENT_ONBOARDER/RELATIONSHIP_MANAGER -> actor.team_id is non-null and equals case.team_id
all malformed/impossible actor/profile combinations -> false
```

Team A and Team B roles have identical visibility. Authorization compares only typed `TeamId`. `client_scope_label` is returned for display but never passed into the decision. No role-specific edit, approval, compliance, escalation, or four-eye permission is added.

For Phase 13, an authenticated actor who can access a case may invoke its existing reads/mutations and may set/clear priority. This is **PROJECT-DEFINED POC BEHAVIOR PENDING SPONSOR CONFIRMATION**, not Delta Capita production policy.

## 10. Director policy

- Director has global case visibility and can invoke existing case operations plus priority mutation on visible cases under the provisional visibility-only policy.
- Director is not assigned to Team A or Team B and receives no user/team administration or security-policy privilege.
- Director-created cases require an explicit typed `team_id` of `TEAM_A` or `TEAM_B`; omission is rejected. No arbitrary or unassigned default is permitted.
- Director can see legacy `team_id=null` cases but cannot create new unassigned cases or reassign them.

## 11. Case-team assignment model

Extend the three existing creation flows (`/api/onboarding/cases`, `/api/clm/cases`, and normal/demo zero-touch creation) through a shared server-side resolver:

- Team actor: the resolver always supplies `actor.team_id`. If any request `team_id` is present, reject it; the client cannot self-assert even the same team.
- Director: request must supply a valid `TEAM_A` or `TEAM_B` value.
- Service calls receive the resolved team and store it when `OnboardingCase` is first created.
- Repository update invariants reject any later change from the persisted non-null `team_id` and any attempt to assign a legacy null case through an ordinary save.
- No reassignment endpoint exists.

## 12. Legacy/unassigned case policy

Version-1 Mongo envelopes and internal/test-created cases without Phase 13 metadata migrate in memory to `team_id=null, priority=null`.

- Team A and Team B users cannot list, read, mutate, or infer these cases.
- Director can list/read/mutate them, including priority, but priority does not assign a team.
- New authenticated HTTP creation cannot produce `team_id=null`.
- No heuristic DBS/OCBC migration, UEN matching, legal-name matching, or automatic reassignment is allowed.

This fail-closed rule is deliberate and should be shown in the demo/runbook.

## 13. Priority model and ordering

Validate request priority as Pydantic strict integer `1 <= priority <= 10` or `None`. Reject `0`, `11`, negatives, floats such as `1.0`/`1.5`, booleans, numeric strings, arrays, and objects with safe `422` detail. JSON `null` clears priority.

Add `PATCH /api/clm/zero-touch/cases/{case_id}/priority` with `{ "priority": 1..10 | null }`. It requires authentication, case access, CSRF, and returns a small authoritative case-priority response or refreshed zero-touch summary. The service acquires the existing per-case lock, reloads the case, rechecks access against current metadata, writes priority, and emits an allowlisted safe audit event.

Canonical list key, descending:

```text
(priority is not null, priority or 0, automation.updated_at, canonical string case_id)
```

This gives `10 > ... > 1 > null`; equal priorities, including two nulls, preserve exactly the current `automation.updated_at DESC, case_id DESC` tie-break. Priority mutation must not rewrite `automation.updated_at` merely to influence order.

The backend query service performs the join, authorization filter, status filter, and final sort. `CaseQueue`, `OnboardedClients`, Audit case discovery, and retained `CasePortfolio`/`ReviewQueue` consumers preserve received order. Frontend search filters may remove rows but must not reorder them.

## 14. Persistence/schema impact

Advance `CASE_SNAPSHOT_SCHEMA_VERSION` from 1 to 2 because stored authorization metadata changes access semantics.

- Create an explicit strict version-1 persistence DTO matching the accepted Phase 12 envelope and a strict version-2 DTO using the extended `OnboardingCase`.
- Decode by exact `schema_version`; reject missing, malformed, and unknown versions.
- Map v1 to an in-memory v2 snapshot with `team_id=null` and `priority=null`; preserve case ID, revision, timestamps, all nested evidence, Decimal strings, target ledger, and demo metadata.
- Do not rewrite during startup or read. The next legitimate CAS mutation may persist version 2 at `revision + 1`.
- New envelopes are version 2 only. No bulk/destructive migration, fallback collection, or silent repair is added.
- Keep one envelope per case and current CAS/identity validation. Add no new collection or duplicated case metadata.
- Memory repositories enforce the same team immutability and priority semantics.
- Sessions remain outside the envelope and are intentionally process-local.

Priority and team metadata must survive composition A -> process restart -> composition B in genuine Mongo tests. Reads/listing after restart remain provider-call free.

## 15. Backend API changes

New endpoints:

| Method/path | Auth policy | Result |
| --- | --- | --- |
| `POST /api/auth/login` | public exact path; JSON + same-origin check | profile, CSRF token, session cookie |
| `GET /api/auth/me` | valid session | current server-authored profile + CSRF token |
| `POST /api/auth/logout` | valid session + CSRF | revoke session and clear cookie |
| `PATCH /api/clm/zero-touch/cases/{case_id}/priority` | valid session + case access + CSRF | authoritative updated priority |

Additive contract changes:

- Creation request may carry `team_id` only for Director creation; the shared resolver enforces actor rules.
- `OnboardingCaseResponse` and zero-touch summary case include `team_id`, `priority`, and a server-projected client-scope label where useful.
- `ZeroTouchCaseListItemResponse` includes `team_id`, `client_scope_label`, and `priority` so list UIs do not fetch or infer access metadata.
- Auth error models use fixed codes/messages and `401`; CSRF uses fixed `403`; inaccessible/missing cases use the same fixed `404` response.
- Do not expose password hashes, session digests, session cookies, CSRF storage internals, or raw auth exceptions in OpenAPI responses.

## 16. Frontend changes

- Add `LoginPage.tsx` matching UI V2 typography/layout with user ID and password fields, generic invalid-login feedback, loading state, and no password persistence.
- Add a focused in-memory auth context/controller that calls login/me/logout, retains profile plus CSRF token only in React memory, and renders the application only after session discovery succeeds.
- Replace `OperatorAccount`/`AccountPlaceholder` with authenticated display name, role, team/client scope, and logout. Director displays global scope without an invented team.
- Centralize `api.ts` network calls in one wrapper that always includes cookies, attaches CSRF to unsafe authenticated requests, handles `401` by clearing auth state, and keeps existing safe error parsing. Do not use `localStorage`, `sessionStorage`, URL tokens, or JS-readable session cookies.
- Add `priority`/team/client-scope fields to `types.ts` and view models.
- Show a compact priority badge in Cases, Review/attention surfaces, Onboarded, and case/client detail. Make 10 visually strongest, mid-range moderate, 1 subtle, and null either absent or “No priority”. Use existing design tokens and accessible text, not color alone.
- Add a priority selector/clear control to authorized case detail. Since every visible actor is provisionally authorized, no role-specific UI branching is needed beyond loading/error/disabled mutation state.
- Preserve backend order. Status/search/jurisdiction filters must use `filter` only; no priority sort is added in React.
- `AuditTrail` loads only authorized case IDs. It may display case priority context, but event chronology remains governed by event timestamps/sequence.
- On startup `401`, show login; on expired session during polling/mutation, stop protected work, clear sensitive case state, and show login. Do not continue stale frontend authorization state.

## 17. Centralized authorization boundary

Preferred request flow:

```text
request
  -> exact public-path check / session authentication
  -> server-authored AuthenticatedActor on request state
  -> CSRF check for unsafe authenticated browser requests
  -> reusable require_case_access(case_id, actor) dependency
  -> existing service/repository operation
  -> authorized response
```

The authentication boundary covers all `/api` paths by default. Public paths are exact allowlist entries, not prefixes. `require_case_access` loads the canonical case and returns the same 404 for absent and cross-team cases. List authorization occurs inside the query service before response projection. Creation uses `resolve_creation_team`; no handler reads team/role headers.

Add an automated route inventory test that introspects FastAPI routes. Every `/api` route must be classified as public, actor-only, case-scoped, or case-creation policy. A newly added unclassified route fails the test.

## 18. Route-by-route authorization coverage map

Public:

- `GET /health`
- `POST /api/auth/login`

Authenticated actor, no case object:

- `GET /api/auth/me`
- `POST /api/auth/logout` (also CSRF)
- `GET /api/system/execution-profile`
- `GET /api/onboarding/mock-scenarios`
- `GET /api/clm/zero-touch/cases` (query service filters by actor before serialization)

Authenticated creation plus server-side team assignment:

- `POST /api/onboarding/cases`
- `POST /api/clm/cases`
- `POST /api/clm/zero-touch/cases`
- `POST /api/demo/clm/zero-touch/cases` (also `demo_controls_enabled`)

Authenticated and case-scoped before any existing service call:

- `GET /api/onboarding/cases/{case_id}`
- `GET /api/clm/cases/{case_id}`
- `POST /api/clm/cases/{case_id}/readiness/evaluate`
- `GET /api/clm/cases/{case_id}/submission-plan`
- `POST /api/clm/cases/{case_id}/submit`
- `POST /api/clm/zero-touch/cases/{case_id}/intake/documents`
- `POST /api/demo/clm/zero-touch/cases/{case_id}/intake/documents`
- `POST /api/clm/zero-touch/cases/{case_id}/intake/documents/{failed_document_id}/retry`
- `POST /api/demo/clm/zero-touch/cases/{case_id}/intake/documents/{failed_document_id}/retry`
- `POST /api/clm/zero-touch/cases/{case_id}/intake/complete`
- `POST /api/demo/clm/zero-touch/cases/{case_id}/intake/complete`
- `GET /api/clm/zero-touch/cases/{case_id}`
- `GET /api/demo/clm/zero-touch/cases/{case_id}/uat-evidence`
- `POST /api/clm/zero-touch/cases/{case_id}/documents`
- `POST /api/clm/zero-touch/cases/{case_id}/documents/{document_id}/replacement`
- `POST /api/demo/clm/zero-touch/cases/{case_id}/documents`
- `POST /api/clm/zero-touch/cases/{case_id}/start`
- `POST /api/clm/zero-touch/cases/{case_id}/resume`
- `POST /api/clm/zero-touch/cases/{case_id}/exceptions/{exception_id}/resolve`
- `POST /api/clm/zero-touch/cases/{case_id}/reconciliation/discrepancies/{discrepancy_id}/resolve`
- `PATCH /api/clm/zero-touch/cases/{case_id}/priority`
- `POST /api/onboarding/cases/{case_id}/ownership/load`
- `POST /api/demo/onboarding/cases/{case_id}/ownership/load`
- `POST /api/onboarding/cases/{case_id}/ownership/analyze`
- `GET /api/onboarding/cases/{case_id}/ownership`
- `GET /api/onboarding/cases/{case_id}/ubo-candidates`
- `POST /api/onboarding/cases/{case_id}/documents`
- `POST /api/demo/onboarding/cases/{case_id}/documents`
- `GET /api/onboarding/cases/{case_id}/documents`
- `GET /api/onboarding/cases/{case_id}/documents/{document_id}`
- `POST /api/onboarding/cases/{case_id}/documents/{document_id}/reviews`

Demo-control checks run after authentication/case authorization so disabled demo routes retain their current safe 404 behavior without leaking cross-team case existence.

## 19. Security threat model

| Threat | Control and required evidence |
| --- | --- |
| Authentication bypass | Default-protect `/api`; exact public allowlist; route-inventory test; malformed/missing/expired cookie -> fixed 401. |
| Role/team spoofing | Ignore authority headers/query/frontend claims; actor comes only from session profile; adversarial spoof tests. |
| IDOR/cross-team access | Canonical `team_id` comparison before every case read/mutation; same 404 for absent/inaccessible; no resource detail in logs/response. |
| Incomplete route protection | Global auth boundary plus route classification and representative cross-team denial for every route family. |
| Frontend-only RBAC | Query service filters and endpoint dependency authorizes before serialization/service mutation. |
| Session fixation/reuse | Rotate/revoke on login, random token, digest-only lookup, one active session/profile, logout/expiry deletion. |
| Session theft impact | HttpOnly, SameSite Strict, host-only, Secure outside loopback, eight-hour absolute TTL, no browser storage/logging. |
| CSRF | In-memory synchronizer token, unsafe-method header check, same-origin checks, no permissive CORS. |
| Credential leakage | `SecretStr`, environment-only hashes, getpass provisioning, fixed errors, safe logging, repository secret scan. |
| User enumeration | Same response and scrypt-cost verification for unknown user and bad password. |
| Token logging | Allowlisted logger fields only; caplog tests assert password/hash/cookie/CSRF/session values absent. |
| Priority validation | Strict integer/null model; boundary and hostile-type tests. |
| Priority authorization | Same case policy and CSRF as other mutation routes; cross-team update returns 404. |
| Memory/Mongo drift | Shared policy/query/sort helper and dual-adapter tests; genuine Mongo restart CI. |
| Legacy data overexposure | v1 -> unassigned; Director only; no label-based migration. |
| Case-team mutation | Immutable repository invariant and no reassignment route. |
| Stored/XSS through profile labels | Fixed source-controlled synthetic labels rendered as React text; no user-defined profile names. |

Safe technical events may include event name, actor `user_id`, role, team ID, case ID, outcome, and timestamp. Login failure must not include the password, hash, cookie, CSRF token, raw request body, or exception. This is ordinary POC technical logging, not a production audit platform.

## 20. Automated test plan

Create focused backend tests for:

### Authentication/session

- Valid login for each of five runtime-configured synthetic users returns the exact server profile, HttpOnly/SameSite cookie, and CSRF token.
- Invalid password and unknown user have the same status/body and do not leak timing path or identity detail.
- Missing, malformed, unknown, and expired sessions return fixed 401 on protected data.
- `/me` returns the server profile; client role/team headers do not change it.
- Login rotates an existing user session; old cookie fails.
- Logout with valid CSRF removes the server session and clears the cookie; reuse fails.
- Missing/wrong CSRF and cross-origin unsafe requests fail; same-origin valid requests pass.
- No credential/session/auth values appear in caplog or API detail.

### Team A / Team B / Director

- Seed Team A and Team B cases with stored IDs unrelated to labels.
- Each Team A profile lists only Team A/DBS display scope; each Team B profile lists only Team B/OCBC.
- Direct detail and representative read/mutation for the other team's learned case ID return the same 404 as a nonexistent ID.
- Run cross-team denial coverage across every route family in section 18; the route-inventory test proves no current case-addressed route is omitted.
- Team users cannot submit `team_id`; Team A cannot create Team B and vice versa.
- Director lists and directly accesses both teams and legacy unassigned cases.
- Director creation without team fails; explicit Team A/Team B succeeds; invalid/null fails.
- `X-Role`, `X-Team`, query `team`, and frontend-shaped role fields never expand access.

### Priority

- Accept `null`, `1`, and `10`; clear `10 -> null`.
- Reject `0`, `11`, negative, float, boolean, string, list, object, missing field, and extra fields.
- Cross-team priority mutation returns 404 and leaves state unchanged.
- Authorized Team users and Director can change visible-case priority under the provisional rule.
- Exact order: `10 > 9 > ... > 1 > null`.
- Equal priority and equal null priority use automation `updated_at DESC`, then canonical case ID DESC.
- Status-filtered lists keep the same priority contract.
- Repeated reads are deterministic and priority mutation does not alter automation timestamps.

### Persistence/migration

- Memory and Mongo adapter doubles produce identical team filtering, priority values, and ordering.
- Strict v1 decode produces Director-only unassigned/null-priority v2 state without writing.
- New/updated data writes schema version 2; unknown versions and malformed team/priority fail closed.
- Team immutability holds in memory and Mongo.
- Genuine Mongo composition A -> B preserves team and all priorities, including null, and lists identically without Registry/IDP/Ownership/GoldTier calls.
- Existing Phase 12 corrupt identity, CAS, interrupted document, uncertain target, and recovery tests remain passing.

### Frontend

- Initial auth loading, valid session, unauthenticated login page, invalid login, logout, and expired-session transition.
- Request wrapper includes cookie credentials and CSRF only where required; no local/session storage.
- Profile display is exact for Team A, Team B, and Director.
- Priority badge/control render, update, clear, loading, 404, 401, 403, 409/5xx safe failure paths.
- Cases, Review, Onboarded, Audit case discovery, and retained list components preserve backend order after filtering.
- Team users cannot navigate to a learned cross-team ID because backend 404 is handled as unavailable.

## 21. Memory/Mongo parity plan

Place the canonical sort helper above persistence adapters and feed it joined `(automation, case)` records. Both persistence modes must call the same helper after access filtering; neither trusts dictionary insertion nor Mongo envelope order.

Use adapter-level tests for fast parity and a separate `test_phase13_real_mongo.py` against Mongo 7 for actual restart evidence. Extend the existing `phase12-mongo` CI job to run both Phase 12 and Phase 13 real-Mongo modules. Local absence of Mongo is a reported skip, never a pass claim.

## 22. Demo seed-data plan

Add `scripts/seed_phase13_demo.py` as an authenticated, idempotent local demo helper:

- Prompt for the Director password with `getpass`; never accept it as a command-line argument or print it.
- Login through the API, keep the cookie/CSRF only in process memory, list existing Director-visible cases, and skip existing fixed synthetic UENs.
- Create at least five Team A and five Team B synthetic zero-touch cases through existing demo routes, using the tracked synthetic UAT documents where progression is needed.
- Assign deterministic priorities across each scope: `10`, `8`, `5`, `1`, and `null`.
- Use Team A/Team B metadata to display DBS/OCBC while all company/document content remains existing synthetic POC data.
- Do not write directly to Mongo, invent real client records, create credentials, or bypass authorization.
- Document memory rerun/restart behavior and Mongo idempotent skip behavior in the demo runbook.

## 23. Sponsor questions and provisional rules

Record one new grouped entry in `docs/sponsor-questions/OPEN_QUESTIONS.md` covering:

- Should Client Onboarder and Relationship Manager have different mutation permissions?
- Who may change case priority?
- Who may reassign a case, and should any reassignment preserve an audit reason/history?
- May a case be shared across teams or have multiple team memberships?
- Is Director globally read-only or permitted existing mutations?
- Does priority drive SLA, escalation, notification, or due-date behavior?
- What production IdP, session/SSO, RBAC, and identity-governance model is expected?

Until answered, record these project-defined POC rules in the decision log and architecture docs:

- role differences govern visibility only;
- any actor with case access may perform existing operations and change priority;
- Director has global visibility and the same existing mutation surface;
- no reassignment/sharing exists;
- priority changes order only and has no SLA/escalation effect;
- local scrypt credentials and process-local opaque sessions are POC-only.

These questions do not block safe Phase 13 execution because the sponsor brief explicitly authorizes provisional behavior.

## 24. Exact files likely to change

Create:

- `apps/backend/app/domain/access.py`
- `apps/backend/app/services/authentication.py`
- `apps/backend/app/services/authorization.py`
- `apps/backend/app/services/case_query.py`
- `apps/backend/app/api_auth.py`
- `apps/backend/tests/test_phase13_auth_rbac.py`
- `apps/backend/tests/test_phase13_priority.py`
- `apps/backend/tests/test_phase13_real_mongo.py`
- `apps/frontend/src/auth.tsx`
- `apps/frontend/src/pages/LoginPage.tsx`
- `scripts/generate_phase13_demo_password_hashes.py`
- `scripts/seed_phase13_demo.py`
- `docs/architecture/PHASE_13_CASE_PRIORITY_AUTH_RBAC.md`
- `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md`

Modify narrowly:

- `apps/backend/app/domain/models.py`
- `apps/backend/app/services/repository.py`
- `apps/backend/app/services/onboarding.py`
- `apps/backend/app/services/clm_orchestration.py`
- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/app/services/zero_touch_repository.py`
- `apps/backend/app/persistence/models.py`
- `apps/backend/app/persistence/mongo_case_store.py`
- `apps/backend/app/persistence/repositories.py`
- `apps/backend/app/persistence/composition.py`
- `apps/backend/app/composition.py`
- `apps/backend/app/config.py`
- `apps/backend/app/api_models.py`
- `apps/backend/app/main.py`
- focused existing API/persistence tests whose clients must authenticate
- `apps/frontend/src/api.ts`
- `apps/frontend/src/types.ts`
- `apps/frontend/src/viewModels.ts`
- `apps/frontend/src/App.tsx`
- `apps/frontend/src/pages/CaseQueue.tsx`
- `apps/frontend/src/pages/CaseDetail.tsx`
- `apps/frontend/src/pages/OnboardedClients.tsx`
- `apps/frontend/src/pages/AuditTrail.tsx`
- `apps/frontend/src/design-system.css`
- `apps/frontend/src/App.test.tsx`
- `apps/frontend/src/UiV2Integration.test.tsx`
- `.github/workflows/ci.yml`
- `docs/PROJECT_CONTEXT.md`
- `docs/decisions/DECISION_LOG.md`
- `docs/sponsor-questions/OPEN_QUESTIONS.md`
- `docs/security/POC_SECURITY_BOUNDARIES.md`
- `docs/integration/CONFIGURATION_REFERENCE.md`
- `docs/demo/DEMO_RUNBOOK.md`
- `.agents/skills/poc-regression-check/references/regression-catalogue.md` only after Phase 13 scenarios pass and are accepted.

Expected unchanged: connector modules/interfaces, GoldTier/ACRA contracts and mappers, `apps/backend/pyproject.toml`, frontend package manifests/lockfile, raw sponsor artefacts, and existing workflow domain policies.

## 25. Integration hotspots

- `main.py`: global protection and case dependencies touch every route. Keep auth endpoints in `api_auth.py`; make route edits mechanical and cover them with inventory tests.
- `api_models.py` + frontend `types.ts`: additive team/priority/profile fields must match exactly.
- `config.py`: hash/cookie/session settings are security-sensitive and must use `SecretStr`/startup validation.
- `composition.py` and persistence composition: share one auth/policy/query instance without duplicating repositories.
- `OnboardingCase` + persistence schema: team immutability and v1 migration must not corrupt Phase 12 envelopes.
- `zero_touch_repository.py`: preserve the accepted automation tie-break while adding priority above it.
- `App.tsx`: keep only auth-shell wiring; put login/session logic in focused components.
- `api.ts`: central wrapper changes all requests; frontend integration tests must prove body/header/file uploads remain correct.
- `.github/workflows/ci.yml`: append Phase 13 Mongo coverage without dropping any job/check.
- Existing untracked workspace item beginning `e workspace and multi-document intake` is unrelated and must remain untouched.

No dependency or lockfile change is justified. If implementation discovers one is necessary, stop and update the plan/security review before adding it.

## 26. Implementation sequence

Each batch starts by recording a `TaskStartSnapshot` (`git status --short`, branch, HEAD) and ends with focused verification. The executor uses the assigned branch, does not switch branches, and does not commit/push unless separately authorized.

### Batch 1 — Auth domain and credential/session service

Files: create `domain/access.py`, `services/authentication.py`, `api_auth.py`; modify `config.py`, composition, and focused tests.

Implement fixed profiles, strict scrypt hash parsing/verification, opaque digest-indexed sessions, TTL/rotation/logout, safe errors, and provisioning script. Verify:

```powershell
cd apps/backend
python -m pytest tests/test_phase13_auth_rbac.py -k "login or session or logout or credential"
python -m ruff check app tests/test_phase13_auth_rbac.py
python -m mypy app
```

### Batch 2 — Central authentication/CSRF and access policy

Files: create/extend auth API boundary and `services/authorization.py`; modify `main.py` minimally.

Default-protect `/api`, exact-allowlist login, attach actor, validate CSRF, add case-access and creation-team resolvers, then classify all routes. Verify auth failures, spoofing, CSRF, 404 non-enumeration, and route inventory.

### Batch 3 — Case team ownership and schema v2 migration

Files: modify case domain, onboarding/CLM/zero-touch creation signatures, repository invariants, persistence DTO/store/adapters, and persistence tests.

Store immutable `team_id`, implement strict v1 read migration to unassigned v2, and preserve all nested Phase 12 evidence/revision behavior. Verify focused migration/immutability tests and existing Phase 12 persistence tests.

### Batch 4 — Authorized portfolio query and priority

Files: create `case_query.py`; modify ordering helper, API models/routes, canonical case/repositories, and focused priority tests.

Add strict priority mutation and shared access-filtered ordering. Verify validation matrix, clear, cross-team denial, tie behavior, status filters, memory/Mongo adapter parity, and deterministic repeated reads.

### Batch 5 — Demo identities and seed data

Files: provisioning/seed scripts and demo/configuration docs.

Generate no committed credential material. Exercise idempotent synthetic Team A/Team B cases and priority spread through authenticated APIs. Verify script unit tests with mocked HTTP/getpass and one local manual run when configured.

### Batch 6 — Frontend session shell and API transport

Files: create `auth.tsx` and `LoginPage.tsx`; modify `api.ts`, `types.ts`, `App.tsx`, and tests.

Centralize cookie/CSRF requests, implement session discovery/login/logout/expiry handling, and render protected UI only for a current profile. Verify frontend auth and existing file-upload/request contracts.

### Batch 7 — Frontend profile/team/priority UI

Files: view models, Cases/CaseDetail/Onboarded/Audit surfaces, retained list components, CSS, and tests.

Add profile scope and accessible priority controls/badges without sorting in the browser. Verify all role presentations, ordering preservation, mutation state, responsive rendering, and current UI V2 behavior.

### Batch 8 — Adversarial, persistence, and regression closure

Run focused route-family cross-team attacks, genuine Mongo restart tests in CI, all Phase 12 recovery tests, full backend/frontend/security/contract/lifecycle suites, and POC regression. Update architecture/context/decision/security/config/demo documents and only then append verified Phase 13 scenarios to the regression catalogue.

## 27. Quality Gate requirements

After implementation and latest-main integration, an independent reviewer must use the project `fyp-quality-gate`, `integration-security-review`, and `poc-regression-check` workflows and write only `.ai-pipeline/reports/PHASE_13_QUALITY_GATE.md` during the gate.

Required commands from repository root, using the configured environment:

```powershell
cd apps/backend
python -m pytest tests/test_phase13_auth_rbac.py tests/test_phase13_priority.py
python -m pytest tests/test_phase12_persistence.py
python -m ruff check .
python -m mypy app
python -m pytest
python -m pip check
python -m unittest discover -s ../../tests/contract -p "test_*.py"
cd ../frontend
npm ls --all
npm run typecheck
npm test
npm run build
cd ../..
python -m unittest discover -s tests -p "test_demo_lifecycle_windows.py" -v
python -m unittest discover -s tests -p "test_check_secrets.py"
python -m unittest discover -s tests -p "test_pre_pr_check.py"
python scripts/check_secrets.py
python scripts/validate_goldtier_examples.py --if-present
git diff --check
```

With Mongo 7 and `PHASE12_MONGO_URI` configured:

```powershell
cd apps/backend
python -m pytest tests/test_phase12_real_mongo.py tests/test_phase13_real_mongo.py
```

After all reviewed feature work is committed, `origin/main` is freshly fetched/merged if advanced, and the tree is clean, run:

```powershell
python scripts/pre_pr_check.py
```

The gate must inspect implementation, not accept test names alone. It must explicitly report authentication/session/CSRF behavior, all case route families, IDOR/non-enumeration, team immutability, priority validation/order, schema migration, genuine Mongo restart, token/log exclusion, UI backend authority, and unchanged POC connector call sequences. Missing genuine-Mongo or route-family evidence prevents PASS.

## 28. Definition of done

Phase 13 is done only when:

- all five environment-provisioned synthetic profiles can login, retrieve current profile, and logout;
- every protected API rejects missing/malformed/expired sessions;
- Team A sees and accesses only Team A/DBS cases; Team B only Team B/OCBC;
- Director sees both teams and legacy unassigned cases without gaining admin features;
- direct cross-team read and mutation attempts return non-enumerating 404 and change nothing;
- all current case-addressable routes are covered by policy and route inventory;
- new cases receive immutable server-resolved teams and cannot impersonate/reassign;
- priority accepts only `1..10 | null`, clears to null, and is authoritatively sorted by the backend;
- equal priority preserves automation `updated_at DESC, case_id DESC`;
- memory and Mongo agree; schema v1 compatibility and schema v2 restart durability pass;
- frontend login/profile/logout/priority UI preserves UI V2 and contains no independent authorization/sorting logic;
- password/hash/session/cookie/CSRF values are absent from source, logs, errors, tests, fixtures, and commits;
- accepted Registry/IDP/reconciliation/ownership/Mock GoldTier behavior and false-success protections pass;
- docs, decision log, sponsor question, security/configuration reference, demo runbook, and verified regression catalogue are current;
- latest `origin/main` is integrated according to protocol, pre-PR check passes on a clean tree, and the independent Phase 13 Quality Gate returns PASS.

## 29. Non-goals

No production SSO/PingFed/AD/OAuth, JWT, MFA, password reset, registration, user/team administration, multi-team membership, case sharing/reassignment, field permissions, role-specific mutation rules, approval/four-eye redesign, priority SLA/escalation/notifications, production identity governance, durable/distributed sessions, production audit platform, real ACRA/GoldTier binding, Sponsor Contract Binding Phase 14, ASIC/MY/HK live integration, or broad UI redesign.

## 30. Risks and rollback considerations

- **Route omission:** mitigated by default `/api` authentication, route classification, and case-family denial tests. Roll back as one auth/access slice only if every protected endpoint is restored consistently; never leave mixed protection.
- **Schema migration defect:** v1 reads are non-writing and fail closed. Preserve original Mongo documents, do not auto-repair, and test exact round trips before enabling v2 writes.
- **Legacy case invisibility:** team users intentionally lose access to unassigned cases. Director visibility plus explicit documentation is the safe operational path; no heuristic migration.
- **Cookie environment mismatch:** Secure cookies do not work over local HTTP. Configuration distinguishes explicit loopback development from production and fails closed on unsafe production settings.
- **CSRF/client-wrapper regression:** central request changes can break uploads or polling. Preserve request bodies/headers and run all frontend integration and workflow tests.
- **Concurrency/lost metadata:** use existing per-case locks and envelope CAS, reload before access/mutation, and enforce immutable team IDs. Phase 13 does not claim multi-instance session or workflow safety.
- **Authentication availability after restart:** sessions intentionally expire on restart and users login again; case state remains durable.
- **Demo credential loss:** hashes are operator configuration, not recoverable application data. Regenerate locally without committing them.
- **Priority misunderstood as risk/SLA:** label priority as queue ordering only in UI/docs; no compliance, risk, or approval claim.
- **Main drift/hotspot conflicts:** fetch before PR readiness, merge current `origin/main` when authorized, reconcile central files by current intent, rerun all checks, and do not rebase the shared branch.

## Execution Readiness View

- Intent Lock: implement only Phase 13 authentication, visibility, team assignment, priority, persistence, demo support, UI integration, and tests.
- Scope Fence: all section 29 non-goals and all connector/business-policy owners remain unchanged.
- Baseline Lock: start from `36d0247befce04bbed85e3dced9f9c1c2b617855`; recheck `origin/main` before implementation/PR readiness according to repository protocol.
- Approved Behavior: five fixed profiles, Team A/DBS, Team B/OCBC, Director global, access-based provisional mutations, strict nullable priority, backend ordering.
- Owner/Contract Constraints: canonical case/envelope, shared policy/query service, no display-string authorization, no frontend sort, no duplicate persistence/auth engine.
- Compatibility Boundary: Phase 01–12 accepted workflows, UI V2, side-effect recovery, ordering tie-break, and connector call stopping.
- Retirement Boundary: POC credential/session adapter is replaceable by future production IAM; team/priority/access contracts remain.
- Task Batches: sections 26.1–26.8 in order; auth/access and schema owners precede route/UI consumption.
- Test Obligations: sections 20, 21, and 27.
- Review Gates: focused verification per batch, integration security review, POC regression, latest-main audit, independent Quality Gate.
- Drift/Rewind Rules: preserve user work; stop on ambiguous contract intent, unexpected overlap, unknown schema, or dependency need; never reset/rebase/clean.
- Evidence Required Before Completion: exact command results, route inventory, adversarial denials, Mongo restart proof, secret/log review, file classification, and PASS gate.
- Advisory Boundary: method-pack execution guidance only; not a `GateDecision`, `PolicySnapshot`, or completion authority.

## Planner readiness decision

**READY FOR EXECUTION** on the assigned Phase 13 branch. No current blocker prevents the bounded POC because unresolved production policies are explicitly isolated as sponsor questions and provisional project behavior. Real PingFed/production IAM and any production RBAC claim remain blocked and out of scope.

**Execution route:** inline, because the implementation has a dense shared security/persistence boundary and this planning task did not authorize subagent implementation. The executor should follow the sequential batches and use independent review only at the Quality Gate.
