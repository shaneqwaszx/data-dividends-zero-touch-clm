# Phase 13 Independent Security + Quality Gate

**Phase:** Case Prioritisation, Authentication & Team-Based RBAC
**Review role:** Fresh independent reviewer
**Review date:** 2026-09-07
**Branch reviewed:** `phase/13-case-priority-auth-rbac`
**Gate result:** **FAIL**

## 1. Executive summary

Phase 13 has a strong centralized authentication/authorization design and the broad automated regression evidence is green. Independent adversarial checks confirmed five fixed profiles, safe login failure behavior, atomic one-session rotation, CSRF enforcement, exact current route classification, bidirectional team isolation, non-enumerating 404 responses, server-owned team assignment, strict priority request validation, and canonical backend priority ordering.

The gate nevertheless fails. Three Medium findings remain: Mongo schema discrimination accepts non-integer numeric lookalikes, frontend priority mutations preserve stale list order and conflate case and automation timestamps, and the genuine-Mongo Phase 13 test does not prove raw schema-v2 retention or team immutability. A Low finding weakens the route-inventory regression guard. In addition, no usable Mongo 7 service was available, so the mandatory genuine-Mongo evidence could not be produced. The planner explicitly prohibits PASS without that evidence.

Critical: **0**
High: **0**
Medium: **3**
Low: **1**

## 2. Baseline

`git fetch origin` completed successfully. The reviewed state matched the requested authoritative baseline:

| Check | Result |
|---|---|
| Branch | `phase/13-case-priority-auth-rbac` |
| `HEAD` | `36d0247befce04bbed85e3dced9f9c1c2b617855` |
| `origin/main` | `36d0247befce04bbed85e3dced9f9c1c2b617855` |
| Merge base | `36d0247befce04bbed85e3dced9f9c1c2b617855` |
| Main drift | None |
| Staged paths | None |

The feature remains an intentionally dirty, owner-controlled working tree. No branch switch, merge, rebase, reset, clean, stage, commit, or push was performed.

## 3. Scope reviewed

The review covered all 24 requested quality-gate areas: architecture ownership; authentication; sessions; cookies; CSRF/origin checks; default auth boundary; route inventory; typed team RBAC; IDOR/non-enumeration; spoofing; creation policy; team immutability; legacy cases; priority validation, authorization, and ordering; schema-v2 persistence; strict schema-v1 compatibility; memory/Mongo parity; recovery evidence; frontend auth/transport/RBAC/ordering; secret/log safety; demo helpers; regression safety; and sponsor-policy truthfulness.

The accepted Phase 12 persistence/recovery architecture and current UI V2 boundaries were inspected where Phase 13 changes them. The unrelated protected untracked filename and all `pytest-cache-files-*` artifacts were not opened, read, modified, renamed, deleted, or treated as findings.

## 4. Planner compliance

Most planner requirements are implemented as designed: fixed synthetic profiles, server-side sessions, centralized route policy, typed team ownership, Director global visibility without administration, server-assigned creation teams, a strict priority HTTP contract, priority-only ordering semantics, schema-v2 envelopes, schema-v1 decoding, and frontend session presentation.

Compliance is incomplete because:

- persistence does not strictly distinguish integer schema versions from `true`, `1.0`, or `2.0`;
- the UI does not re-acquire server ordering after priority mutation;
- required genuine-Mongo evidence is unavailable and the Phase 13 real-Mongo test omits two required assertions.

Pre-PR readiness: **NOT YET APPLICABLE UNTIL OWNER-CONTROLLED COMMIT**.

## 5. Architecture review

The implementation has one canonical owner for each reviewed responsibility:

- `OnboardingCase` owns `team_id` and `priority`;
- `AuthenticationService` owns profiles, credential verification, sessions, rotation, expiry, and logout;
- the authorization policy and middleware own access decisions;
- `CaseQueryService` owns authorized projections and backend ordering;
- the Phase 12 envelope remains the persistence owner;
- `AuthProvider` and the request wrapper provide browser presentation/transport only.

No duplicate case model, persistence engine, case authorization implementation, client-name authorization, or independent frontend priority sorter was found. The frontend stale-order behavior in Finding P13-QG-002 is a synchronization defect, not a second policy engine.

## 6. Authentication review

**Authentication: PASS**

Exactly these five typed profiles are defined: `team-a-onboarder`, `team-a-rm`, `team-b-onboarder`, `team-b-rm`, and `director`. Hashes are supplied through `SecretStr` configuration. No plaintext password or reusable committed credential hash was found. Missing and malformed profile configuration fail closed.

Credential verification uses fixed `hashlib.scrypt` parameters (`N=16384`, `r=8`, `p=1`, `dklen=32`, bounded memory), random salts for generated hashes, a dummy derivation for unknown users, and `hmac.compare_digest`. Independent HTTP checks confirmed the same fixed failure response for unknown identity and wrong password. Documentation consistently describes this as local POC authentication, not production IAM.

## 7. Session review

**Session lifecycle: PASS**

Sessions use opaque `secrets.token_urlsafe(32)` values; only SHA-256 digests are stored. TTL is an absolute eight hours. The in-process store is bounded, one session is retained per profile, relogin revokes the old session, logout removes server state, expired entries are purged, and process restart intentionally invalidates all sessions. No session value is logged.

The shared lock covers purge, old-session removal, new-session insertion, authentication, logout, and count operations. No opposing lock acquisition was found.

## 8. Session-race remediation review

**Concurrent session rotation: PASS**

The previously reported race was independently targeted. Twelve rounds of eight simultaneous same-profile logins and twelve login-versus-logout rounds were run. All 24 rounds ended with exactly one valid session for the profile. The lock makes the rotation mutation atomic and includes stale-session cleanup. Focused tests also cover expiry and HTTP rotation. No deadlock or lock inversion was observed in the bounded review.

## 9. Cookie review

Cookies are `HttpOnly`, `SameSite=Strict`, host-only, and scoped to `Path=/api`. Production requires the Secure setting and rejects insecure configuration; explicit loopback development/test is the documented exception. An independent production-cookie probe confirmed `Secure`, `HttpOnly`, `SameSite=strict`, no `Domain`, and `/api` path. The frontend stores neither a JS-readable session value nor an auth token in `localStorage`, `sessionStorage`, or URLs.

## 10. CSRF/origin review

**CSRF: PASS**

Unsafe authenticated requests require `X-CSRF-Token`; the synchronizer value comes from the server session and stays in frontend memory. Validation is constant-time. Origin/Referer are checked for same-origin when supplied, login is JSON-only, and no permissive credentialed wildcard CORS policy was added.

Independent checks produced the same safe 403 response for missing token, incorrect token, and cross-origin unsafe requests. The correct token succeeded.

## 11. Route inventory

**Route inventory: PASS for the current application; regression guard has a Low finding.**

Recursive inspection of FastAPI's included routers produced exactly 42 current routes and an exact match with the policy inventory:

| Policy class | Count |
|---|---:|
| Public | 2 |
| Actor-only | 5 |
| Case creation | 4 |
| Case scoped | 31 |
| Total | 42 |

The only public endpoints are `GET /health` and `POST /api/auth/login`. All other `/api` endpoints require an actor. The case-scoped set covers onboarding, CLM, zero-touch, demo, documents, retry, reviews, ownership, UBO, readiness, submission, reconciliation, exceptions, start/resume, UAT evidence, and priority. No current route is unclassified or backed by stale policy.

Finding P13-QG-004 records that the automated test enumerates only top-level `APIRoute` values and uses subset comparison; in this FastAPI version it sees 39 rather than all 42 routes.

## 12. Team/RBAC review

**Team A isolation: PASS**
**Team B isolation: PASS**
**Director visibility: PASS**

Authorization compares typed `team_id`. `TEAM_A` and `TEAM_B` map to DBS and OCBC display scopes, respectively, but those labels are never authorization inputs. Onboarder and RM profiles for a team have identical case visibility. The Director has `team_id=null`, global case visibility, and only the existing mutation surface; no user/team administration was added.

No authorization comparison based on legal name, UEN, registration pattern, registry data, client label, or frontend-provided team string was found.

## 13. IDOR/non-enumeration evidence

**IDOR/non-enumeration: PASS**

An independent bidirectional matrix exercised all 31 case-scoped route policies: Team A against Team B identifiers and Team B against Team A identifiers. Sixty-two cross-team attempts matched absent-case responses in status and safe body shape (`404`, approved `CASE_NOT_FOUND` equivalent). Representative denied priority and workflow mutations left state unchanged.

Authorization occurs before case details are exposed, so the result does not reveal whether a cross-team identifier exists.

## 14. Spoofing evidence

Headers (`X-Team`, `X-Role`), query team/role values, and frontend-shaped role/team request values did not alter the authenticated server profile or expand access. Body-supplied team identifiers are rejected on team-actor creation and cannot override server assignment.

## 15. Creation/team immutability evidence

All four creation families—onboarding, CLM, zero-touch, and demo—were independently exercised. Team A and Team B creators received server-assigned teams. Team actors could not submit either a matching or different `team_id`. Director omission, null, and invalid teams were rejected; explicit `TEAM_A` and `TEAM_B` succeeded. No authenticated HTTP creation produced `team_id=null`.

**Team immutability: FAIL** as a complete gate criterion. Memory and Mongo-adapter tests confirm non-null teams cannot be changed and legacy null is not assigned by unrelated mutation, and no reassignment endpoint exists. However, mandatory genuine-Mongo proof was unavailable, and the existing Phase 13 real-Mongo test never attempts a team mutation (Finding P13-QG-003).

## 16. Legacy case policy

Schema-v1 decode maps `team_id=null` and `priority=null`. Team actors cannot see legacy-unassigned cases; the Director can. Reads do not rewrite the source envelope. No heuristic DBS/OCBC assignment exists. The semantic legacy policy passes, but the discriminator's type strictness fails as documented in Finding P13-QG-001.

## 17. Priority validation

**Priority validation: PASS**

The accepted values are exactly JSON `null` and integers 1 through 10. Independent requests verified acceptance of `null`, `1`, and `10`, and 422 rejection of `0`, `11`, `-1`, `1.0`, `1.5`, `true`, `false`, `"1"`, arrays, objects, a missing field, and extra fields. Rejected requests left the existing value unchanged.

## 18. Priority authorization

`PATCH /api/clm/zero-touch/cases/{case_id}/priority` requires authentication, case authorization, and CSRF. Authorized actors can set, update, and clear priority under the documented provisional POC policy. Cross-team attempts return the non-enumerating 404 and preserve state.

## 19. Priority ordering

**Priority ordering: FAIL overall; backend ordering PASS, frontend preservation FAIL.**

Independent backend probes produced exact order `10, 9, 8, 7, 6, 5, 4, 3, 2, 1, null`. Equal priorities and null ties both used `automation.updated_at DESC`, then `case_id DESC`. Status-filtered output retained the canonical order and repeated reads were deterministic. Priority mutation did not change `automation.updated_at`.

The frontend contains no competing `.sort()` call. It nevertheless mutates rows in place without fetching a newly ordered projection, so a server sequence such as `[10, 1, null]` becomes `[10, 1, 9]` after changing the last row to priority 9. This violates the requirement to preserve backend authority; see P13-QG-002.

## 20. Persistence schema-v2 review

**Schema v2 persistence: FAIL**

New envelopes write version 2 and preserve the Phase 12 nested evidence. Unknown versions, malformed team, malformed priority, `_id`/`case_id` mismatch, and invalid revisions fail closed. Revision compare-and-swap remains. The same collection and persistence engine are retained; no bulk repair or silent migration was introduced.

The decoder, however, selects versions using Python numeric equality. A raw `schema_version=2.0` is accepted as v2 rather than rejected as malformed. This violates the required strict version contract (P13-QG-001).

## 21. Schema-v1 compatibility

**Schema v1 compatibility: FAIL**

Valid v1 records decode to the current model with null team/priority and are not rewritten on read. Unknown fields remain rejected. Independent malformed-envelope probes showed that `schema_version=true` and `schema_version=1.0` are both treated as version 1 and migrated in memory. Strict compatibility therefore is not satisfied (P13-QG-001).

## 22. Genuine Mongo evidence

**Genuine Mongo restart: UNAVAILABLE**
**GENUINE MONGO EVIDENCE: UNAVAILABLE**

`PHASE12_MONGO_URI` was not configured. Docker CLI 29.7.2 was installed, but its engine pipe was unavailable; Docker Desktop could not bring up the stopped `com.docker.service`, and standalone `mongod` was absent. Processes started solely for the check were stopped. No container or repository configuration was left behind.

The separate test command completed as `12 skipped in 0.61s`; it did not exercise Mongo. This mandatory evidence gap independently prevents PASS.

## 23. Memory/Mongo parity

Memory and the Mongo adapter double pass the Phase 12/13 repository contract, including priority, team fields, legacy decode, CAS, and provider-free recovery behavior. **Parity remains only partially evidenced** because a genuine Mongo service could not be used. The authored physical-Mongo coverage gap is separately recorded in P13-QG-003.

## 24. Frontend auth review

**Frontend auth: PASS**

`AuthProvider` resolves `/me` before mounting protected workspace content. Valid login, invalid login, restore, logout, and 401 transition are covered. A 401 clears the in-memory actor/CSRF state and unmounts the protected `App`, returning to login. No stale frontend identity authorizes requests.

The centralized request wrapper uses `credentials: include`, adds CSRF only to unsafe authenticated calls, preserves JSON requests and `FormData` uploads, and retains existing polling/header/error behavior.

## 25. Frontend RBAC/priority review

**Frontend priority/RBAC: FAIL**

Team A, Team B, and Director scopes are presented correctly; Director is shown as global rather than assigned to a fake team. Priority can be set and cleared. The UI does not make authorization decisions and does not use DBS/OCBC labels as security inputs.

The priority UI fails the ordering-authority requirement after mutation and also overwrites list/detail timestamps with the case mutation timestamp even where the list contract exposes the automation timestamp. See P13-QG-002.

## 26. Secret/log review

**Secret/log safety: PASS with a bounded scan limitation.**

Static inspection and tests found no usable plaintext credential, stable demo password/hash, session token, cookie token, CSRF secret, or raw Authorization value committed in the Phase 13 delta. Authentication values are not logged; invalid-login and authorization paths emit only safe identifiers/statuses.

The five secret-check unit tests passed. The exact `python scripts/check_secrets.py` entry point was intentionally not run because it enumerates every untracked file and would open the user-protected artifact. The same scanner implementation was invoked with only that protected path and the protected cache directories excluded: 379 files scanned, 0 findings. This preserves the explicit workspace boundary rather than treating it as a defect.

## 27. Demo helper review

The password-hash generator uses `getpass` with confirmation, a fresh salt, the approved scrypt helper/parameters, prints only environment hash assignments, never prints plaintext, and writes no file automatically.

The seed helper obtains Director credentials without embedding them, uses authenticated HTTP APIs rather than Mongo, is idempotent, creates synthetic Team A/Team B cases, and covers priorities `10, 8, 5, 1, null`. Its focused tests passed; a manual seed was not required.

## 28. Sponsor-policy truthfulness

Documentation consistently labels the following as provisional POC behavior: Onboarder/RM shared mutation surface, any authorized actor changing priority, Director's global use of the same existing surface, no reassignment, no sharing, priority as ordering only, no SLA/escalation meaning, and local credentials/sessions as non-production. Q-016 remains open. No UI or documentation was found claiming production Delta Capita RBAC policy.

## 29. Compatibility/regression review

**Existing CLM regressions: PASS**

The feature delta preserves the jurisdiction gateway, ACRA Mock, IDP, reconciliation, ownership/UBO, Mock GoldTier, multi-document intake, restart recovery, connector call stopping, false-success protections, and UI V2 structure. External systems remain behind connector/service interfaces. No connector contract was changed.

The selected current-catalogue POC regression set passed 443 tests. The full backend suite, 44 contract tests, frontend suite, and 17 Windows lifecycle checks also passed. The lifecycle rerun left no `.runtime/demo-processes.json` and no listener on ports 8000/5173.

## 30. Exact test evidence

| Evidence command/check | Result |
|---|---|
| Focused Phase 13/12 pytest | 58 passed |
| Full backend pytest | 802 passed, 12 skipped (real Mongo only) |
| Separate Phase 12/13 real-Mongo pytest | 12 skipped; service unavailable |
| Ruff | Pass |
| mypy | Success, 78 source files |
| `pip check` | No broken requirements |
| Contract unittest discovery | 44 passed |
| Current-catalogue POC regression selection | 443 passed |
| Frontend dependency tree | Valid; optional unmet peers only |
| Frontend typecheck | Pass |
| Frontend Vitest | 102 passed across 3 files |
| Frontend production build | Pass, 45 modules transformed |
| Windows demo lifecycle | 17 passed |
| Secret-check unit tests | 5 passed |
| Pre-PR-check unit tests | 37 passed |
| Protected-boundary-safe secret scan | 379 files, 0 findings |
| GoldTier example validation | 19 valid; 19 invalid/quarantined; 48 not validated; exit 0 |
| Independent current-route flattening | 42/42 exact match |
| Bidirectional case-policy adversarial matrix | 62/62 safe denials |
| Concurrent-session stress | 24/24 rounds retained one valid session |
| Priority exact-order probe | Exact `10..1,null`; ties/filter/repeats pass |
| `git diff --check` | Exit 0; line-ending warnings only |

Some Windows process-spawning commands initially encountered sandbox `EPERM`/temporary-directory permission failures. Qualifying reruns with the same test scope outside that restriction produced the pass results above. The first mypy invocation used an invalid `NUL` cache target; the qualifying rerun used an isolated writable cache and passed.

The three Pydantic warnings in the full/regression suites are from existing adversarial construction tests and are not Phase 13 failures.

## 31. Dependency audit

No dependency change was introduced. `apps/backend/pyproject.toml`, `apps/frontend/package.json`, and `apps/frontend/package-lock.json` are unchanged. The CI change extends the existing real-Mongo job to include Phase 13 tests; it does not add a package or service contract.

## 32. Diff audit

Before this report, the tracked delta was 47 modified files, 913 insertions, and 157 deletions. `git diff --check` passed and no path was staged.

Changed paths classify as:

- backend Phase 13 auth/RBAC/priority/persistence wiring and focused compatibility updates;
- frontend auth, identity/scope presentation, priority UI, and related tests/styles/types;
- Phase 13 tests plus necessary authenticated-client updates to existing tests;
- CI real-Mongo coverage, regression catalogue, architecture/contracts/security/configuration/demo/project documentation, and sponsor decision/question records;
- Phase 13 planner/execution artefacts, demo scripts, and test support.

The delta contains no package manifest, `.env`, credential file, raw sponsor artefact, new persistence collection, or connector contract. The unrelated protected filename and inaccessible cache artefacts remain untracked and untouched. `docs/aegis/` was pre-existing Phase 13 process state and was not changed by this independent gate.

## 33. Findings

### P13-QG-001 — Medium — Schema-version discriminator accepts non-integer lookalikes

`apps/backend/app/persistence/mongo_case_store.py:187-194` branches with `schema_version == 1` and `schema_version == CASE_SNAPSHOT_SCHEMA_VERSION`. Python treats `true == 1`, `1.0 == 1`, and `2.0 == 2`; model validation then coerces these values. Independent probes confirmed v1 migration for `true` and `1.0`, and v2 acceptance for `2.0`.

**Impact:** malformed persistence envelopes do not fail closed, weakening schema migration safety and strict v1/v2 compatibility.

**Required remediation:** require an exact integer discriminator before branching (excluding booleans and floats), retain unknown-version handling, and add v1/v2 regression cases for boolean and floating-point versions.

### P13-QG-002 — Medium — Priority mutation leaves frontend order stale and changes timestamp semantics

`apps/backend/app/api_models.py:665-681` defines list `updated_at` as `automation.updated_at`, while the priority response at lines 685-701 returns `case.updated_at`. `apps/frontend/src/pages/CaseQueue.tsx:161-165` replaces the priority and list timestamp in place; `OnboardedClients.tsx:131-135` also updates in place; `CaseDetail.tsx:140` substitutes the case timestamp into summary fields.

**Impact:** after a mutation, the displayed queue can violate `10..1,null` until a later reload and can display a timestamp with a different meaning from the list contract. This is material to the sponsor-demo prioritisation behavior.

**Required remediation:** after a successful priority mutation, refetch the authorized server-ordered projection (without client sorting) and preserve the automation timestamp semantics supplied by that projection. Add a frontend test that changes a low/null row to a higher priority and asserts the resulting server order.

### P13-QG-003 — Medium — Genuine-Mongo Phase 13 test omits required durability assertions

`apps/backend/tests/test_phase13_real_mongo.py:55-119` proves restart visibility, team/priority values, ordering, and provider-free reads, but does not inspect the raw stored `schema_version` and does not attempt a forbidden team reassignment across a genuine Mongo save/reload.

**Impact:** even when CI has Mongo, the authored test does not prove two explicit gate requirements: version 2 retained on disk and team immutability persisting through the physical adapter.

**Required remediation:** extend the genuine-Mongo test to assert the stored v2 discriminator and to prove a non-null team cannot be changed (including after composition restart), while retaining Phase 12 recovery coverage.

### P13-QG-004 — Low — Route inventory regression test omits included routers

`apps/backend/tests/test_phase13_auth_rbac.py:460-473` enumerates only top-level `APIRoute` objects and asserts `actual <= route_inventory()`. With the current FastAPI router representation, it observes 39 routes and omits the three auth routes held by an included router. Independent recursive flattening showed the present inventory is nevertheless exactly 42/42.

**Impact:** a future unclassified route added through an included router might not fail this regression test. There is no current unclassified route or current authorization bypass.

**Required remediation:** recursively flatten included routers (or derive the full application route set through a stable supported mechanism) and assert equality, not subset inclusion.

## 34. Final metrics

| Metric | Result |
|---|---:|
| Critical | 0 |
| High | 0 |
| Medium | 3 |
| Low | 1 |
| Current routes deliberately classified | 42/42 |
| Independent bidirectional policy denials | 62/62 |
| Backend tests | 802 passed, 12 skipped |
| Frontend tests | 102 passed |
| Contract tests | 44 passed |
| POC regression selection | 443 passed |
| Genuine Mongo | Unavailable |

Explicit gate statuses:

| Area | Status |
|---|---|
| Authentication | PASS |
| Session lifecycle | PASS |
| Concurrent session rotation | PASS |
| CSRF | PASS |
| Route inventory | PASS |
| Team A isolation | PASS |
| Team B isolation | PASS |
| Director visibility | PASS |
| IDOR/non-enumeration | PASS |
| Team immutability | FAIL |
| Priority validation | PASS |
| Priority ordering | FAIL |
| Schema v1 compatibility | FAIL |
| Schema v2 persistence | FAIL |
| Genuine Mongo restart | UNAVAILABLE |
| Frontend auth | PASS |
| Frontend priority/RBAC | FAIL |
| Secret/log safety | PASS |
| Existing CLM regressions | PASS |

## 35. Remaining limitations

- No genuine Mongo 7 runtime was available, so physical storage, restart, schema-v2, immutability, and parity claims remain unverified locally.
- The protected workspace artifact prevented use of the repository scanner's unfiltered entry point; the same scanner ran over the permitted file set with zero findings.
- This is a review-only result on an uncommitted owner-controlled delta. Latest-main integration and the production pre-PR check remain outside this gate until the owner commits the intended work.
- Confidence grade: **B**. Direct target and broad regression evidence are strong, but mandatory physical-Mongo evidence is absent and the identified Medium defects prevent readiness.

Evidence classification: test counts and adversarial probe results are **measured**; code/diff behavior and the stopped lifecycle state are **observed**; UI stale-order impact is **inferred** directly from the observed state transition; POC policy authority is **declared** by the reviewed project records; genuine-Mongo runtime behavior is **unknown** in this environment.

### Aegis impact and safety receipt

- **Key judgment:** current security isolation is sound, but strict persistence, UI ordering, and mandatory physical-Mongo evidence do not meet the Phase 13 completion boundary.
- **Avoided misfix:** no implementation, test accommodation, fallback, or owner-controlled Git action was introduced during this review.
- **Boundary held:** review-only scope; only this report was created; protected untracked/cache artefacts were untouched.
- **Baseline alignment:** implementation drift from the accepted Phase 13 contract in schema discrimination and frontend ordering, plus missing verification authority for genuine Mongo.
- **Complexity control:** no product-code complexity was added by the gate; remediation should tighten the existing owners rather than add parallel authorization, ordering, or persistence paths.
- **Evidence strength:** fresh focused/full/backend/frontend/contract/lifecycle/regression/security checks plus independent adversarial probes; confidence B.
- **Uncovered risk:** physical Mongo behavior, raw v2 persistence, and physical-adapter team immutability remain unproved.
- **Next most valuable verification:** remediate the three Medium findings and rerun the genuine Mongo 7 Phase 12/13 suites with the added raw-schema and immutability assertions.

## 36. Final verdict

Critical and High counts are zero, but Medium is non-zero and mandatory genuine-Mongo evidence is unavailable. Phase 13 is not ready for owner-controlled integration. Remediate P13-QG-001 through P13-QG-003, strengthen P13-QG-004, then rerun the focused, full, frontend, contract, lifecycle, secret, POC regression, independent adversarial, and genuine-Mongo checks.

FAIL — PHASE 13 REQUIRES REMEDIATION
