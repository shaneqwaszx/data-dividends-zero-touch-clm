# Phase 13 Demo Authentication and Identity Remediation

## Scope and baseline

- Branch: `fix/phase13-demo-login-identities`
- `BASE_SHA`, initial `HEAD`, and fetched `origin/main`:
  `dcb52937d46882a5b1b6ba7f2d545829e6fda662`
- Scope: the post-Phase-13 Vite-proxy login failure, synthetic operator identities,
  user-facing team metadata, frontend identity presentation, credential generator,
  authenticated seeder, and directly affected documentation/tests.
- Non-goals held: no ACRA/GoldTier connector behavior, UBO/business rule, persisted
  team identifier, case persistence schema, authorization policy, dependency, or Phase
  14 change.

## Root cause and repair

### Observed failure

A direct pre-change reproduction used a valid runtime-only credential with a backend
TestClient whose request origin was `http://127.0.0.1:8000` and browser header was
`Origin: http://127.0.0.1:5173`. Login returned:

- HTTP `403`
- `CSRF_VALIDATION_FAILED`

The middleware rejected the request before password verification.

### Root cause

`api_auth.py` compared each supplied Origin/Referer only with `request.url` scheme and
network location. In the supported browser architecture, Vite receives the browser
request at `http://127.0.0.1:5173` and proxies `/api` to FastAPI at
`http://127.0.0.1:8000`. The backend-visible request origin can therefore differ from
the browser origin even though the browser is using the documented local topology.

### Origin policy before and after

Before:

- absent Origin/Referer was accepted;
- a supplied Origin/Referer had to match the backend-visible request origin;
- the documented Vite browser origin could be rejected before credentials were checked.

After:

- `BrowserOriginPolicy` is the single HTTP validation owner;
- true same-origin requests remain accepted;
- development/test additionally trusts exactly `http://127.0.0.1:5173`;
- no wildcard, hostname pattern, arbitrary origin, or localhost alias was added;
- production receives an empty additional-origin set and remains true-same-origin only;
- malformed/foreign Origin or Referer still returns the fixed
  `CSRF_VALIDATION_FAILED` response;
- authenticated unsafe requests still require both an accepted browser origin (when a
  header is present) and the session-bound `X-CSRF-Token`.

The policy is derived from `Settings.app_env`; it is not client-controlled and has no
production environment override that could silently inherit the local Vite origin.

## Synthetic identity mapping

| User ID | Display name | Role | Internal team |
|---|---|---|---|
| `maya-lim` | Maya Lim | `CLIENT_ONBOARDER` | `TEAM_A` |
| `ethan-tan` | Ethan Tan | `RELATIONSHIP_MANAGER` | `TEAM_A` |
| `sophia-ng` | Sophia Ng | `CLIENT_ONBOARDER` | `TEAM_B` |
| `ryan-lee` | Ryan Lee | `RELATIONSHIP_MANAGER` | `TEAM_B` |
| `olivia-koh` | Olivia Koh | `DIRECTOR` | none/global |

These are explicitly synthetic POC identities. All functional Phase 13 code, tests,
scripts, and current documentation use the new IDs. Historical planner/execution and
quality-gate reports remain unchanged as records of the accepted pre-remediation state.

## User-facing team mapping

| Persisted ID | Display name | Team type | Coverage | Canonical description |
|---|---|---|---|---|
| `TEAM_A` | DBS Corporate Onboarding | Corporate Client Onboarding | DBS | Type: Corporate Client Onboarding \| Client coverage: DBS |
| `TEAM_B` | OCBC Corporate Onboarding | Corporate Client Onboarding | OCBC | Type: Corporate Client Onboarding \| Client coverage: OCBC |

`TEAM_A` and `TEAM_B` are unchanged in the domain and persisted case data. No
persistence migration was introduced. The canonical `Team` model owns the display
name, team type, coverage, and derived description. Authenticated profile responses
project the caller's team metadata and backend-authored available team options; the
frontend does not infer access. Olivia Koh is rendered as global/cross-team rather than
as a member of either team.

## Credential settings and local migration

The credential settings now follow the new stable synthetic IDs:

- `PHASE13_MAYA_LIM_PASSWORD_HASH`
- `PHASE13_ETHAN_TAN_PASSWORD_HASH`
- `PHASE13_SOPHIA_NG_PASSWORD_HASH`
- `PHASE13_RYAN_LEE_PASSWORD_HASH`
- `PHASE13_OLIVIA_KOH_PASSWORD_HASH`

The old five setting names are not compatibility aliases because silently binding an
old technical account credential to a different identity would obscure the migration.
Local users must rerun:

```powershell
python scripts/generate_phase13_demo_password_hashes.py
```

Copy only the five emitted hashes into the local untracked `.env`. The generator still
uses hidden prompts, emits only scrypt hashes, and never persists or prints plaintext.
Missing or malformed hashes still fail startup with only the relevant setting name.

## Frontend and demo behavior

- The login field accepts the person-like IDs and uses `maya-lim` only as a username
  placeholder. No password or password hint is embedded.
- The signed-in account immediately shows display name, role, team display name, and
  coverage/global scope. Its disclosure shows the canonical team description.
- Director team selection is rendered from backend-returned canonical team metadata;
  the backend continues to validate the submitted persisted TeamId.
- `seed_phase13_demo.py` authenticates as `olivia-koh`, retains five cases per team,
  priorities `10, 8, 5, 1, null`, Team A to DBS and Team B to OCBC, API-only seeding,
  and no direct Mongo writes.

## Verification evidence

### Focused and broad automated checks

| Check | Result |
|---|---|
| Pre-change local Vite-origin reproduction | `403 CSRF_VALIDATION_FAILED` with a valid runtime-only credential |
| Focused Phase 13 backend command | 61 passed |
| Frontend typecheck | PASS |
| Frontend Vitest | 104 passed |
| Frontend production build | PASS, 45 modules transformed |
| Contract suite with existing helper directory on `PYTHONPATH` | 44 passed |
| Windows demo lifecycle | 17 passed in 190.63 seconds |
| Full backend suite | 823 passed, 12 skipped, 3 existing serializer warnings |
| Ruff | PASS; inaccessible pre-existing `pytest-cache-files-*` directories produced warnings only |
| Mypy | PASS, 78 source files |
| `pip check` | PASS |
| Secret scanner unit tests | 5 passed |
| Pre-PR checker unit tests outside sandbox | 37 passed |
| Task-owned secret scan | 27 files including this report, 0 findings |
| `git diff --check` plus report trailing-whitespace scan | PASS |

The exact root-level contract command initially failed collection because
`phase13_contract_credentials` is located under `tests/contract` but that directory was
not importable. Rerunning the same suite with
`PYTHONPATH=apps/backend;tests/contract` collected and passed all 44 tests. No product
code was changed to accommodate this environment/path issue.

### Actual demo start and frontend-proxy evidence

`tests/test_demo_lifecycle_windows.py` invokes `scripts/start_demo_windows.bat` against
the real local launcher and verifies both endpoints. Its primary start/stop test now
POSTs login through:

`http://127.0.0.1:5173/api/auth/login`

with browser Origin `http://127.0.0.1:5173`. The request returned HTTP `200` and the
profile identified `maya-lim` / Maya Lim. The suite then verified and stopped the exact
launcher-owned process trees. This is measured end-to-end HTTP proxy evidence. Visual
browser automation was not used so a credential would not be placed in automation
commands or logs.

## Security invariant review

- Public surface remains exactly login plus `/health`; route inventory tests pass.
- Sessions remain server-side, opaque, process-local, rotated, bounded, and one-active-
  session-per-profile.
- The cookie remains host-only, HttpOnly, `SameSite=Strict`, `/api`, and Secure in
  production; production insecure-cookie startup still fails closed.
- Authenticated unsafe mutations still require the session-bound CSRF token.
- Foreign Origin and Referer values are rejected independently.
- Team/role identity and team-option metadata are backend-authored. Request headers,
  query parameters, bodies, localStorage, and sessionStorage do not become identity
  authorities.
- Cross-team inaccessible and absent cases retain identical safe `404` behavior;
  Director global access remains intact.
- No plaintext password, reusable hash, token, cookie, CSRF value, KYC/PII, or raw
  external payload was added to source, docs, normal logs, or frontend storage.
- No CORS wildcard, CSRF bypass, connector change, TLS change, or new dependency was
  introduced.

## Files changed

Backend/authentication and tests:

- `apps/backend/app/api_auth.py`
- `apps/backend/app/composition.py`
- `apps/backend/app/config.py`
- `apps/backend/app/domain/access.py`
- `apps/backend/app/main.py`
- `apps/backend/tests/phase13_test_clients.py`
- `apps/backend/tests/test_phase13_auth_rbac.py`
- `apps/backend/tests/test_phase13_demo_scripts.py`
- `apps/backend/tests/test_phase13_priority.py`
- `apps/backend/tests/test_phase13_real_mongo.py`

Frontend and tests:

- `apps/frontend/src/App.tsx`
- `apps/frontend/src/design-system.css`
- `apps/frontend/src/pages/LoginPage.tsx`
- `apps/frontend/src/types.ts`
- `apps/frontend/src/App.test.tsx`
- `apps/frontend/src/Phase13AuthPriority.test.tsx`
- `apps/frontend/src/UiV2Integration.test.tsx`

Scripts, lifecycle, and documentation:

- `scripts/generate_phase13_demo_password_hashes.py`
- `scripts/seed_phase13_demo.py`
- `tests/test_demo_lifecycle_windows.py`
- `docs/PROJECT_CONTEXT.md`
- `docs/architecture/PHASE_13_CASE_PRIORITY_AUTH_RBAC.md`
- `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md`
- `docs/decisions/DECISION_LOG.md`
- `docs/demo/DEMO_RUNBOOK.md`
- `docs/integration/CONFIGURATION_REFERENCE.md`
- `.ai-pipeline/reports/PHASE_13_DEMO_AUTH_IDENTITY_REMEDIATION.md`

## Limitations and process incident

- This remains local POC authentication, not PingFed/SSO, production RBAC, distributed
  sessions, rate limiting, account lockout, or identity governance. Q-016 remains open.
- The unfiltered `scripts/check_secrets.py --help` invocation unexpectedly ran the
  scanner because the script ignores command-line arguments. Its candidate enumeration
  includes non-ignored untracked files, so it may have read the protected unrelated
  untracked filename beginning `e workspace and multi-document intake`. It did not
  modify, stage, delete, or print that file or its contents. All subsequent secret
  scanning was restricted to task-owned tracked diff paths. This prevents an unqualified
  claim that the protected file was never opened/read during the task.
- The pre-existing `pytest-cache-files-*` artifacts were not modified or removed.

## Git state and handoff

Final `HEAD`, fetched `origin/main`, and merge base all remained
`dcb52937d46882a5b1b6ba7f2d545829e6fda662`; `HEAD..origin/main` was empty.
Final state is intentionally uncommitted. No file was staged, committed, pushed,
merged, rebased, reset, cleaned, or branch-switched. The unrelated untracked entries
present at task start remain untracked and were not modified. The tracked working tree
contains the 26 task-owned modifications listed above, the remediation report is a new
untracked task-owned file, and `git diff --cached --name-only` was empty.

Recommended next action: review the report and diff, regenerate the five local hashes,
and perform an owner-controlled commit/PR workflow only if the remediation is accepted.
