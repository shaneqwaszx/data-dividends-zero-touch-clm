# Phase 15C Frontend URL Navigation — Implementation Evidence

## Baseline, scope, and classification

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-15c`
- Branch: `phase/15c-frontend-navigation`
- Assigned `BASE_SHA`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Start and completion `HEAD`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Completion `origin/main`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Change classes: `FRONTEND_UI`, `FRONTEND_STATE_CACHE`,
  `AUTH_RBAC_SECURITY`, `ARCHITECTURE_REFACTOR`, and `DOCS_ONLY`.
- The pre-existing untracked planner was preserved. This run added its authorized
  execution addendum and this implementation report.
- No staging, commit, push, PR, merge, rebase, reset, stash, clean, branch switch, or
  sibling-worktree change was performed.

## Implemented navigation ownership

`BrowserRouter` is mounted once outside `AuthProvider`, and the browser URL is now the
only page and case navigation identity. `App` no longer owns an independent active-page,
selected-case, selected-client, or audit-case navigation state. Page tabs, cards, queue
links, client links, case links, and audit case filters now navigate through real
same-origin links.

The retained intake operation is intentionally not a second navigation owner. It only
retains the immutable identity and browser-only inputs of an explicitly initiated live
operation while the tab remains mounted. Once a case exists, its canonical intake URL
is `/new-onboarding/:caseId`.

| Route | Destination | Required capability / behavior |
|---|---|---|
| `/` | Capability-safe default redirect | First accessible workspace destination |
| `/dashboard` | Dashboard | `CASE_ACCESS` |
| `/new-onboarding` | New onboarding | `CASE_ACCESS` |
| `/new-onboarding/:caseId` | Retained intake or recovery | `CASE_ACCESS`; UUID only |
| `/cases` | Case queue | `CASE_ACCESS` |
| `/cases/:caseId` | Case detail | `CASE_ACCESS`; UUID only |
| `/onboarded` | Onboarded clients | `CASE_ACCESS` |
| `/onboarded/:caseId` | Completed-client detail | `CASE_ACCESS`; UUID only |
| `/audit` | Audit trail | `CASE_ACCESS` |
| `/audit/:caseId` | Case-filtered audit trail | `CASE_ACCESS`; UUID only |
| `/policy` | Policy administration | `POLICY_VIEW` |
| `/admin/users` | User administration | `IDENTITY_ADMIN` |
| `/admin/teams` | Team administration | `TEAM_ADMIN` |
| any other application path | Generic unavailable screen | No protected-resource read or business mutation |

Malformed case identifiers, capability-unavailable destinations, and unknown paths use
the same generic unavailable presentation and do not echo attacker-controlled path
content. A non-completed case cannot be presented as an onboarded client. Absent,
deleted, and inaccessible cases preserve the backend-authoritative indistinguishable
`404` boundary.

## Router and architecture decision

- Added exact dependency `react-router@7.18.4`; existing React `18.3.1`, React DOM
  `18.3.1`, React Query `5.102.8`, TypeScript, Vite, and Vitest versions were not
  upgraded.
- The lockfile adds the router and its direct package graph (`cookie` and
  `set-cookie-parser`).
- `ADR-001_FRONTEND_URL_NAVIGATION.md` records the durable choice as **Proposed**;
  `DECISION_LOG.md` records proposed technical decision D-043 without claiming sponsor
  approval.
- `ARCHITECTURE.md` now records URL ownership, router placement, retained-intake
  boundaries, safe route behavior, and deployment fallback requirements.

## Auth, cache, and response-publication safety

- `AuthProvider` remains the authentication/session owner. The router neither stores nor
  transports credentials or tokens. Login restores on the originally entered safe
  same-origin path rather than serializing a return target into a query string.
- Existing logout, identity-change, and `401` cancellation/clearing remain owned by the
  existing auth and query-client modules; those owners were not edited.
- Existing user/session-scoped React Query keys, team scope, Director team-filter
  identity, and `AbortSignal` forwarding remain intact.
- Unknown, malformed, and capability-unavailable application routes disable App-level
  profile/team reads and mount no protected destination.
- Case A detail, document, ownership, and audit responses are aborted or confined to
  Case A. Delayed Case A responses cannot publish under a Case B route.
- Route changes do not place credentials, tokens, UENs, names, document text, KYC
  evidence, selected filenames, or other sensitive values into the URL/history. Only
  opaque case UUIDs are accepted.
- No persistent sensitive browser cache was added.

## Intake safety

The live intake operation is bound to one operation generation, actor identity, case ID,
and selected `File` objects. After a successful create, the URL is replaced with the
case-specific intake route before document intake continues. Route remount and React
Strict Mode effect replay do not recreate a case, duplicate an upload, or repeat intake
completion.

A late create response does not steal navigation if the user has already left the
originating onboarding destination. Returning through the onboarding link reaches the
retained operation URL. Ordinary browser refresh cannot restore `File` objects and does
not pretend otherwise: `/new-onboarding/:caseId` performs GET-only recovery, displays
actual retained backend case/document state, explains that browser-selected files were
not restored, and offers safe recovery actions. Refresh does not retry a create, upload,
or completion request.

Route mounting, direct entry, refresh, Back, and Forward issue no new business mutation.
Existing read/poll behavior remains with its existing destination owners.

## Deployment fallback evidence

The supported local launcher/Vite composition was exercised with ephemeral in-memory
demo credential hashes; no `.env` file or persisted credential was accessed. The local
HTTP evidence was:

| Request | Result |
|---|---|
| `GET /cases/<uuid>` | `200 text/html`; exact SPA index |
| `GET /new-onboarding` | `200 text/html`; exact SPA index |
| `GET /policy` | `200 text/html`; exact SPA index |
| `GET /unknown-application-path` | `200 text/html`; exact SPA index |
| `GET /api/does-not-exist` | `401 application/json`; not SPA index |
| `GET /assets/does-not-exist.js` | `404`; not SPA index |
| `POST /cases/:caseId` | `404`; not SPA index |

This demonstrates the local development fallback only. A deployment host must rewrite
eligible **GET/HEAD application routes** to `index.html` while excluding `/api/*`,
`/assets/*`, existing static files, and non-navigation methods. No production host was
available or tested, so production history fallback is explicitly unverified.

In a real Chrome session, direct entry at `/cases/<uuid>` preserved the exact URL while
showing the login boundary; reload preserved it; `/new-onboarding` followed by browser
Back and Forward restored the exact case and onboarding paths. Authentication was not
performed in that browser session because the ephemeral credential was intentionally
discarded. The authenticated login-and-return boundary is instead covered by automated
test P15C-NAV-07. Real case-link `href`/new-tab semantics are covered by P15C-NAV-04.

## Files

Added:

- `.ai-pipeline/001_planner/PHASE_15C_EXECUTION_ADDENDUM.md`
- `.ai-pipeline/reports/PHASE_15C_IMPLEMENTATION.md`
- `apps/frontend/src/navigation.tsx`
- `apps/frontend/src/pages/RetainedIntakeRecovery.tsx`
- `apps/frontend/src/Phase15CNavigation.test.tsx`
- `docs/decisions/ADR-001_FRONTEND_URL_NAVIGATION.md`

Modified:

- `apps/frontend/package.json`
- `apps/frontend/package-lock.json`
- `apps/frontend/src/main.tsx`
- `apps/frontend/src/App.tsx`
- `apps/frontend/src/pages/Dashboard.tsx`
- `apps/frontend/src/pages/CaseQueue.tsx`
- `apps/frontend/src/pages/OnboardedClients.tsx`
- `apps/frontend/src/pages/ClientDetail.tsx`
- `apps/frontend/src/pages/AuditTrail.tsx`
- `apps/frontend/src/App.test.tsx`
- `apps/frontend/src/Dashboard.test.tsx`
- `apps/frontend/src/UiV2Integration.test.tsx`
- `apps/frontend/src/Phase14_5AdminPolicy.test.tsx`
- `apps/frontend/src/Phase14CaseManagementPerformance.test.tsx`
- `docs/ARCHITECTURE.md`
- `docs/decisions/DECISION_LOG.md`

The existing `.ai-pipeline/001_planner/PHASE_15C_FRONTEND_NAVIGATION.md` remains
untracked and unchanged as the planner-owned handoff.

## Verification evidence

| Check | Result |
|---|---|
| P15C-NAV-01 through P15C-NAV-16 | PASS — 15 tests; NAV-10/11 share one Strict Mode test; fresh completion rerun passed 15/15 |
| Focused Phase 15C + Phase 14 performance + Phase 13 auth + Dashboard regression | PASS — 46 tests |
| Full frontend test suite | PASS — 170 tests across 8 files |
| Frontend typecheck | PASS |
| Frontend production build | PASS — 108 modules; JS 344.53 kB / gzip 100.30 kB; CSS 59.25 kB |
| Exact dependency tree | PASS — React/DOM 18.3.1, React Query 5.102.8, `react-router` 7.18.4 |
| `npm audit --omit=dev` | PASS — 0 production vulnerabilities |
| Full npm audit | BASELINE ADVISORIES — 4 development-tool findings in the existing Vitest/Vite/nanoid graph (1 moderate, 2 high, 1 critical); no production/router finding |
| Full backend pytest | PASS — 980 passed, 14 skipped; 3 pre-existing Pydantic warnings |
| Ruff check | PASS |
| Ruff format check | BASELINE FAILURE — 30 unchanged backend/script files would be reformatted; Phase 15C has no backend/script diff and did not reformat out-of-scope files |
| Mypy | PASS — 91 source files |
| Contract unittest suite | PASS — 44 tests |
| Secret unit tests | PASS — 8 tests |
| `python scripts/check_secrets.py` | PASS |
| `python scripts/check_project_state.py` | PASS |
| `python scripts/check_architecture.py` | PASS |
| `python scripts/dev_context.py` | PASS at task start and completion |
| `git diff --check` | PASS before and after report creation |

The Windows lifecycle suite passed 17/18 on its first complete run after the local
environment was installed, with the single failed case passing immediately in focused
rerun. A second aggregate run passed 16/18 before transient endpoint-health loss; both
reported cases passed together in focused rerun, and the earlier reset case also passed
focused. No lifecycle implementation was changed. This is recorded as an aggregate
harness/service-liveness residual, not represented as a green full-suite result.

Historical SSR-style tests emit React Router `useLayoutEffect` server-render warnings;
they do not fail and do not indicate a client-runtime route failure. The ignored local
`.venv` used for repository checks is not a tracked artifact. Final runtime cleanup left
no process manifest or listener on ports 8000/5173.

The first completion-only Vitest rerun was blocked by Windows sandbox process creation
(`spawn EPERM` while starting esbuild). The same command was immediately rerun with the
required process permission and passed 15/15; this was an environment restriction, not
a test failure.

## Security and POC regression review

The Phase 15C integration-security review found no new issue: backend authorization
remains authoritative; only opaque UUID case IDs enter routes; unavailable cases keep
the safe `404` boundary; unknown routes are inert; errors remain sanitized; no
persistent sensitive cache was introduced; and no route mount performs a business
mutation.

The POC regression review found no change to backend workflow ordering, accepted mock
scenarios, terminal states, connector call-stopping behavior, or Mock/Local/Sandbox/
Partial/Dormant provider labels. The full backend suite passed and the POC catalogue
requires no Phase 15C update. Physical Mongo testing was not relevant because Phase 15C
changes neither persistence nor backend behavior.

## Phase 15B overlap and non-goals

Phase 15B retains ownership of review/rework backend planning and implementation,
including new review controls and continue-after-retry semantics. Phase 15C did not edit
backend routes, frontend API/types/query/auth owners, review/rework behavior, contracts,
or the Phase 15B worktree. The retained `ReviewQueue` business selection prop is not a
page/case navigation owner and was left for its owning phase.

There is no API, shared model/type, persistence schema, connector, provider, GoldTier,
ACRA, document-extraction, business-rule, mapping, deployment-host configuration, or
provider-status change. No external integration or physical database was activated.

## Completion boundary and residual risk

The implementation is complete within the authorized Phase 15C file boundary, and its
direct frontend acceptance evidence is green. Confidence is **B** because production
history fallback is untested and the full Windows lifecycle aggregate remained flaky
despite every observed failure passing focused rerun. The unchanged Ruff-format debt and
development-tool audit advisories remain baseline issues outside this phase.

The next required action is an independent Phase 15C quality gate, including deployment-
host fallback verification when an authorized target is available and an independent
assessment of the lifecycle aggregate flake. This report is implementation evidence
only; it does not self-approve the phase or authorize commit, push, PR, merge, or
deployment.

## Remediation after independent QG FAIL

**Date:** 2026-09-19  
**Status:** `REMEDIATION IMPLEMENTED — LIFECYCLE INFRASTRUCTURE BLOCKER REMAINS`

This appended section preserves the historical evidence above and the independent QG
report. The execution addendum now records the owner's narrow refinement: CaseDetail
action-lifetime safety and local Vite static-namespace correction are in scope;
lifecycle tooling remains read-only; and production hosting remains a later
deployment-owner dependency. No backend, lifecycle, auth/query, API/type, CI,
dev-tooling, production-hosting, Phase 15B, or sibling-worktree file was changed.

### F-01 — case-bound action lifetime: remediated

The QG finding was reproduced before remediation: local dialog/busy/error state survived
an in-place `/cases/A` to `/cases/B` parameter change, while asynchronous Case A
completions were not uniformly guarded before publishing state or navigating.

`CaseDetail` now captures an immutable action identity containing generation, case ID,
and actor user ID. Route/actor replacement invalidates it and clears local case-action
presentation. Every relevant post-`await` cache effect, state publication, error, busy
reset, dialog callback, and delete navigation verifies the operation remains current.
An issued backend request is not cancelled or rolled back.

Executed router-integrated tests using the real `CaseDetail` prove that Case A delete
and disclosure dialogs close rather than retarget Case B; stale Case A delete success
cannot navigate B away; stale A failure cannot publish into B; B cannot be mutated from
A state; and Back/Forward cannot migrate an action between route identities.

### F-02 — local Vite static namespace: remediated

The original report claimed missing `/assets/**` returned `404`. The independent QG
correctly reproduced `GET /assets/does-not-exist.js` as `200 text/html` with the SPA
shell. Root cause: Vite's development HTML fallback accepted an unresolved static-
namespace request before final index transformation.

The Vite 7.1.11 development configuration now records the original URL before Vite's
middleware and installs a post-static/post-history boundary. Existing public,
transformed, and static assets retain normal handling. Only unresolved `/assets` or
`/assets/**` requests reaching that boundary receive `404 text/plain`. Query strings,
decoded/encoded paths, nested names, GET, and HEAD are covered. The boundary owns no
application routing, API behavior, or business logic.

Fresh execution against an actual Vite server loaded from the repository config proved:

| Request | Fresh remediation result |
|---|---|
| `GET /cases/<synthetic-uuid>` | `200 text/html`; exact test SPA index |
| `HEAD /cases/<synthetic-uuid>` | `200 text/html`; empty HEAD body |
| `GET /new-onboarding` | `200 text/html`; exact test SPA index |
| `GET /policy` | `200 text/html`; exact test SPA index |
| `GET /unknown-application-path` | `200 text/html`; exact test SPA index |
| `GET /api/auth/me` unauthenticated | `401 application/json`; not index HTML |
| `GET /assets/does-not-exist.js` | `404 text/plain`; not index HTML |
| `GET /assets/nested/does-not-exist.css?cache=1` | `404 text/plain`; not index HTML |
| `GET /assets/%64oes-not-exist.js` | `404 text/plain`; not index HTML |
| `HEAD /assets/does-not-exist.js` | `404`; empty HEAD body |
| `GET /assets/existing.css` | `200 text/css`; real known asset body |
| `POST /cases/<synthetic-uuid>` | `404`; not index HTML |

This is local-development evidence only. Production-host fallback remains **UNVERIFIED —
LATER DEPLOYMENT-OWNER DEPENDENCY**.

### F-03 — Windows lifecycle: unchanged infrastructure blocker remains

Before the single aggregate run, the dev-tooling lifecycle run had completed, ports
8000/5173 were free, no manifest remained, the repository interpreter was selected,
and lifecycle scripts/tests were unchanged from `BASE_SHA`.

The full run started `2026-09-19T13:20:37.1249495Z`, ended
`2026-09-19T13:25:31.4492011Z`, and took `294.324` seconds. It ran 18 tests: **17 passed,
1 failed, 0 errors**. The only failure was
`test_reset_with_missing_backend_record_does_not_start`: after the deliberately missing
backend ownership record made reset fail closed, the expected original backend health
endpoint was unavailable.

Only that first causal test was then run once. It started
`2026-09-19T13:26:12.6232275Z`, ended `2026-09-19T13:26:18.6707720Z`, and took `6.048`
seconds. It failed during initial startup (`1` run, `0` passed, `1` failed, `0` errors):
the frontend log recorded `spawn EPERM` when esbuild attempted to start while Vite was
loading its config, and cleanup recorded `Access denied` while terminating the owned
backend process tree. These are Windows process-spawn/process-termination infrastructure
failures before the focused test reaches an HTTP fallback assertion. The same Vite
configuration passed the actual HTTP test, full frontend suite, and build, while 17
lifecycle tests ran successfully in the aggregate.

No lifecycle code, test, timeout, ownership rule, or backend behavior was changed.
Cleanup matched the retained backend PID to the manifest's executable and exact UTC
creation time, terminated only that launcher-owned process, and used the lifecycle stop
command to clear metadata. Final state: ports 8000/5173 free and
`.runtime/demo-processes.json` absent. The failed aggregate is not represented as green.

### F-04 — live-intake race falsification: evidence completed

Six deterministic deferred-promise tests settle stale create, upload, and completion
callbacks after explicit fresh reset/navigation and after real `AuthProvider`
logout/replacement login. They prove stale work cannot steal the route, repopulate the
new journey, start a follow-on upload/completion, duplicate an operation, reactivate an
old operation, publish old-user state, or expose old-user cache evidence. Issued backend
work is not claimed to be rolled back. All passed against the existing `App` owner, so
no production `App` remediation was needed.

### Fresh remediation verification

| Check | Result |
|---|---|
| Phase 15C navigation/action/intake tests | PASS — 25/25; includes 4 F-01 and 6 F-04 tests |
| Actual Vite HTTP fallback test | PASS — 1/1 scenario test; all requests above asserted |
| Phase 15C focused total | PASS — 26/26 across 2 files |
| Phase 15C + Phase 14 performance + Phase 13 auth + Dashboard | PASS — 57/57 across 5 files |
| Full frontend suite | PASS — 181/181 across 9 files |
| Frontend typecheck | PASS |
| Frontend build | PASS — 108 modules; JS 345.33 kB / gzip 100.62 kB; CSS 59.25 kB / gzip 12.65 kB |
| Dependency inventory | PASS — React/DOM 18.3.1, React Query 5.102.8, `react-router` 7.18.4, Vite 7.1.11, TypeScript 5.9.3 |
| `npm audit --omit=dev` | PASS — 0 production vulnerabilities; system CA used after a certificate-store failure without disabling TLS |
| Full backend pytest | PASS — fresh exit 0; unchanged collection: 980 passed, 14 skipped (994 total) |
| Ruff check | PASS |
| Ruff format check | BASELINE FAILURE — unchanged 30-file backend/script debt; no out-of-scope reformat |
| Mypy | PASS — 91 source files |
| Contract unittest suite | PASS — 44 tests |
| Secret unit tests | PASS — 8 tests |
| Secret, project-state, and architecture scripts | PASS |
| `git diff --check` | PASS |
| Windows lifecycle aggregate | BLOCKED — 17/18 passed; one failure; focused test also failed from process infrastructure |
| Physical Mongo | NOT APPLICABLE |

React Router SSR-style `useLayoutEffect` warnings remain non-failing output. No
sensitive value or persistent browser cache was introduced.

### Files and architecture self-check

Remediation-specific changes are:

- `.ai-pipeline/001_planner/PHASE_15C_EXECUTION_ADDENDUM.md`
- `.ai-pipeline/reports/PHASE_15C_IMPLEMENTATION.md`
- `apps/frontend/src/pages/CaseDetail.tsx`
- `apps/frontend/vite.config.ts`
- `apps/frontend/src/Phase15CNavigation.test.tsx`
- `apps/frontend/ViteHistoryFallback.test.ts`

`App.tsx` was not changed by remediation because the new F-04 tests passed. The
independent `.ai-pipeline/reports/PHASE_15C_QUALITY_GATE.md` remains unchanged.

**ARCHITECTURE REMEDIATION SELF-CHECK: WITHIN AUTHORIZED BOUNDARY**

The URL remains the sole page/case navigation identity; no selected-case/page state,
router loader/action, auth owner, query/cache owner, or workflow owner was added.
`CaseDetail` owns local actions for exactly one current case/actor/generation. Vite owns
only local development HTTP namespace behavior. Backend authorization/case existence,
`AuthProvider`, React Query, and `App` retain their existing responsibilities. No
lifecycle or dev-tooling responsibility was absorbed.

ADR-001 remains **Proposed**. Phase 15B remains independent; no Phase 15B source or
worktree was inspected or copied. There is no API/shared-type, persistence schema,
provider, connector, mapping, business-rule, security-authority, or production-host
configuration change.

F-01, F-02, and F-04 are closed with executed evidence. Phase 15C acceptance remains
stopped solely on the demonstrably unchanged Windows lifecycle/process infrastructure
blocker. This is implementer remediation evidence, not an independent QG verdict, and
authorizes no stage, commit, push, PR, merge, or deployment.

## Manual Windows lifecycle verification after remediation

**Date:** 2026-09-20  
**Current implementation status:** `REMEDIATION VERIFIED — READY FOR INDEPENDENT RE-QG`

The repository owner subsequently executed the complete Windows lifecycle suite
manually from normal Windows CMD. Before execution, the owner confirmed that ports 5173
and 8000 had no listeners and `.runtime/demo-processes.json` was absent.

Exact command:

```cmd
".venv\Scripts\python.exe" -m unittest discover -s tests -p "test_demo_lifecycle_windows.py" -v
```

- Interpreter: this worktree's `.venv\Scripts\python.exe`.
- Result: **PASS — 18/18 tests** (`OK`).
- Duration: **266.225 seconds**.
- Pre-run state: ports 5173 and 8000 free; runtime manifest absent.
- Post-run state: ports 5173 and 8000 free; runtime manifest absent, independently
  rechecked during this evidence closeout.
- Lifecycle source, tests, timeouts, and ownership behavior remain unchanged; no
  lifecycle remediation was made.

This successful uncontended manual execution closes the lifecycle evidence blocker. All
earlier aggregate and focused lifecycle failures remain preserved above as historical
evidence. This status is implementation readiness for a new independent quality gate;
it is not an independent QG verdict and grants no authority to stage, commit, push,
create a PR, merge, rebase, reset, stash, clean, or deploy.

## Non-assets static resource fallback remediation

**Date:** 2026-09-20  
**Current implementation status:**
`REMEDIATION VERIFIED — READY FOR ADVERSARIAL PRE-QG FALSIFICATION`

### Root cause and correction

The latest independent re-QG proved that missing non-`/assets` JavaScript, CSS, image,
and font paths still returned `200 text/html` with the SPA shell. The focused real-Vite
test reproduced this before correction: `/missing.js` returned `200` instead of `404`.

Vite 7.1.11's development `htmlFallbackMiddleware` treats unresolved GET/HEAD requests
as SPA candidates when `Accept` is absent, contains `text/html`, or contains `*/*`.
The prior Phase 15C post-history boundary retained the original URL but rejected only
the `/assets` namespace, so every other resource-like miss could continue into
`indexHtmlMiddleware` after Vite rewrote the request to `/index.html`.

The existing Vite serve plugin remains the sole owner. Its post-static/post-history,
pre-index boundary now classifies unresolved requests deterministically from:

1. the reserved `/assets` namespace;
2. a resource-valued `Sec-Fetch-Dest` such as script, style, image, font, manifest,
   worker, media, embed, or object;
3. a case-insensitive set of established web/static extensions covering scripts,
   modules, styles, source maps, images, fonts, manifests/data, media, documents, and
   WebAssembly;
4. resource-oriented `Accept` values; or
5. any other dotted final path segment that does not explicitly request `text/html`.

The query string is excluded before classification and the pathname is URL-decoded
once. If decoding is malformed, a visible raw extension still classifies the request.
This is not a blanket “pathname contains a period” rule: an unknown dotted wildcard
navigation such as `/reports/quarter.v2` remains eligible for the SPA shell when it
explicitly requests HTML as a document. Known resource extensions remain resources even
if an adversarial request sends `Accept: text/html`.

Existing resources are served by Vite's proxy/public/transform/static middleware before
this boundary. Only unresolved resource/API requests reach the new `404 text/plain`
response. `/api/**` remains proxy-first and cannot fall through to SPA HTML. Unsafe
methods remain outside Vite's history rewrite. HEAD uses the same classification as GET
and returns an empty response body.

No React Router route table was copied into Vite, no application business rule was
introduced, and navigation, auth, React Query, backend RBAC, CaseDetail action identity,
intake generation containment, lifecycle, API, schema, and provider owners were not
changed.

### Real-server adversarial evidence

`ViteHistoryFallback.test.ts` starts the actual configured Vite server against an
isolated fixture root and makes real loopback HTTP requests. Its harness now reserves an
explicit free loopback port because Vite's `port: 0` path can fall back to 5173 and
collide with an unrelated listener.

Fresh passing assertions include:

- every declared SPA route, `/`, direct case/onboarding/onboarded/audit deep links, and
  an unknown navigation path -> `200 text/html` with the exact SPA marker;
- dotted wildcard document navigation `/reports/quarter.v2` -> SPA shell;
- known `/assets/known.css` and root `/known-root.js` -> their real resource bodies and
  CSS/JavaScript content types;
- missing `/assets/**` ordinary, nested, query-bearing, and encoded variants -> `404`,
  never SPA HTML;
- missing `/missing.js`, `/modules/missing.mjs`, `/foo/missing.css`,
  `/images/missing.png`, `/fonts/missing.woff2`, and `/maps/missing.js.map` -> `404`,
  never SPA HTML;
- uppercase, query-bearing, encoded-dot, encoded-slash, and malformed-encoding resource
  paths -> `404`, never SPA HTML;
- an unknown `.custom` resource with `Accept: application/octet-stream` -> `404`;
- extensionless `Sec-Fetch-Dest: image` request -> `404` even with `Accept: text/html`;
- favicon and web-manifest misses -> `404`;
- HEAD for representative JavaScript, CSS, and image misses -> `404` with an empty body;
- `/api/auth/me` and `/api/missing.js` with adversarial `Accept: text/html` -> backend
  JSON `401`/`404`, never SPA HTML; and
- POST, PUT, PATCH, and DELETE against both navigation and resource paths -> `404`,
  never SPA HTML.

### Verification and governance

| Check | Fresh result |
|---|---|
| Initial focused falsification | RED — `/missing.js` returned `200`, expected `404` |
| Final real-Vite resource test | PASS — 1/1 scenario with the adversarial matrix above |
| Phase 15C navigation + real-Vite focused tests | PASS — 26/26 across 2 files |
| Full frontend suite | PASS — 181/181 across 9 files |
| Frontend TypeScript | PASS |
| Frontend production build | PASS — 108 modules; JS 345.33 kB / gzip 100.62 kB; CSS 59.25 kB / gzip 12.65 kB |
| Architecture check | PASS |
| Project-state check | PASS |
| Secret scan | PASS |
| `git diff --check` | PASS; line-ending warnings only |
| Backend/contracts | NOT RERUN — no backend, API, contract, model, persistence, provider, or business behavior changed |
| Physical Mongo | NOT APPLICABLE |

The accepted manual Windows lifecycle evidence remains 18/18 PASS in 266.225 seconds.
It was not rerun because lifecycle/root startup code and lifecycle-owned files were not
changed, and the actual Vite test freshly proved server startup plus healthy `/` SPA
response behavior. Final cleanup left ports 5173 and 8000 free and no runtime manifest.

Remediation-specific files for this slice:

- `apps/frontend/vite.config.ts`
- `apps/frontend/ViteHistoryFallback.test.ts`
- `.ai-pipeline/reports/PHASE_15C_IMPLEMENTATION.md`

Architecture self-check: **PROCEED within the existing Vite/static-server owner**. No
new cross-layer route authority, dependency, navigation owner, fallback service, or ADR
change was introduced. ADR-001 remains **Proposed**. Both independent quality-gate
reports remain immutable historical evidence.

This is implementer evidence for adversarial verification, not an independent PASS.
Production-host fallback remains an unverified later deployment-owner dependency. No
stage, commit, push, PR, merge, rebase, reset, stash, clean, branch switch, latest-main
integration, or deployment is authorized or performed.

## HTTP classifier bypass remediation

**Date:** 2026-09-20  
**Current implementation status:**
`REMEDIATION VERIFIED — READY FOR SECOND ADVERSARIAL FALSIFICATION`

The independent HTTP falsifier found four real-server false-success paths. Each
returned `200 text/html` with the SPA shell before this remediation:

1. An extensionless request with `Sec-Fetch-Dest: empty` was admitted because the
   classifier treated only named resource destinations as negative evidence; `empty`
   was not positive document-navigation evidence, but the earlier negative heuristic
   still let the request reach Vite's fallback.
2. `/foo%252Ejs` was admitted because the pathname was decoded only once, leaving a
   still-encoded dot that the extension classifier could not see.
3. `/trailing-dot.` was admitted because the extension expression required at least
   one character after the dot and therefore returned no extension.
4. `Accept: text/html;q=0` was admitted because a substring check treated the mere
   presence of `text/html` as consent, without evaluating its quality value.

The repaired boundary uses positive SPA navigation admission. An unresolved request
may proceed to Vite's SPA fallback only when it is `GET` or `HEAD`, every safely derived
pathname form is neither `/api/**` nor resource-like, the request explicitly accepts
`text/html` with a valid quality value greater than zero, and `Sec-Fetch-Dest` is absent
or is `document`, `frame`, or `iframe`. A present `empty`, `script`, `style`, `image`,
`font`, `worker`, or other non-document destination is denied. Vite's real resource and
proxy middleware retains first opportunity to handle the request; the boundary applies
only to unresolved requests and does not duplicate the React Router route table.

HTML acceptance is parsed by comma-separated media ranges and semicolon-separated
parameters. Media types and parameter names are case-insensitive, whitespace is
trimmed, an absent `q` defaults to 1, valid positive qualities admit the request, and
`q=0`/`q=0.000`, duplicate `q`, malformed `q`, wildcard-only, and non-HTML media ranges
do not. A mixed list is admitted only when its `text/html` range itself has `q > 0`.
The request's Accept media type is normalized before Vite 7.1.11's case-sensitive
history-fallback precondition so uppercase `TEXT/HTML` retains correct HTTP semantics.

Path canonicalization retains the raw pathname and performs at most three deterministic
`decodeURIComponent` rounds, stopping when stable. Any derived form that exposes a
known resource extension, `/assets/**`, `/api/**`, or a terminal-dot final segment
denies SPA fallback. Malformed encodings fail closed. If a percent-encoded octet remains
after the third round, the path is ambiguous and also fails closed. This covers `%2E`,
`%252E`, and `%25252E` without unbounded recursive decoding. Terminal-dot paths such as
`/trailing-dot.` and `/nested/path..` are denied, while dotted document paths remain
eligible when explicit HTML/document evidence is present.

### Fresh real-server adversarial evidence

The actual configured Vite server was started on `127.0.0.1:5173`; these probes were
separate from the automated fixture matrix:

| Probe | Result |
|---|---|
| triple-encoded resource + HTML/document | `404 text/plain; charset=utf-8`, no SPA shell |
| double-encoded resource + HTML/document | `404 text/plain; charset=utf-8`, no SPA shell |
| terminal-dot + HTML/document | `404 text/plain; charset=utf-8`, no SPA shell |
| unknown-extension + HTML/document | `200 text/html`, SPA shell (positive document evidence) |
| extensionless + wildcard Accept + `empty` destination | `404 text/plain; charset=utf-8`, no SPA shell |
| `text/html;q=0` + document | `404 text/plain; charset=utf-8`, no SPA shell |
| `text/html;q=0` + no destination | `404 text/plain; charset=utf-8`, no SPA shell |
| wildcard Accept + no destination | `404 text/plain; charset=utf-8`, no SPA shell |
| extensionless + HTML/document positive control | `200 text/html`, SPA shell |

Server cleanup left ports 5173 and 8000 free and
`.runtime/demo-processes.json` absent.

### Fresh verification

| Check | Result |
|---|---|
| Pre-fix real-Vite falsifier regression | RED — all four reported bypasses returned SPA HTML; uppercase HTML media type also exposed Vite's case-sensitive precondition |
| Focused real-Vite fallback test | PASS — 1/1 test with Accept, destination, encoding, resource, API, method, HEAD, and static-resource variants |
| Focused fallback + Phase 15C navigation tests | PASS — 26/26 across 2 files; F-01 and F-04 remain closed |
| Full frontend suite | PASS — 181/181 across 9 files; existing SSR `useLayoutEffect` warnings only |
| Frontend TypeScript | PASS |
| Frontend production build | PASS — 108 modules transformed |
| Architecture check | PASS |
| Project-state check | PASS |
| Secret scan | PASS |
| `git diff --check` | PASS; line-ending warnings only |
| Backend/contracts | NOT RERUN — no backend, API, shared contract/model, persistence, provider, auth, cache, or business behavior changed |
| Phase 15C Windows lifecycle | NOT RERUN — accepted evidence remains 18/18 PASS in 266.225 seconds; lifecycle/root startup ownership was unchanged |

Remediation-specific files remain limited to:

- `apps/frontend/vite.config.ts`
- `apps/frontend/ViteHistoryFallback.test.ts`
- `.ai-pipeline/reports/PHASE_15C_IMPLEMENTATION.md`

Architecture review remains **PROCEED within the existing Vite/static-server owner**:
the change narrows the established development fallback boundary, adds no dependency or
second route owner, and requires no ADR amendment. Production-host history fallback is
still deployment-owner work and has not been claimed as verified. This is implementer
evidence only; a second independent adversarial falsification is still required.

## Vite-first HTTP fallback architecture remediation

**Date:** 2026-09-20  
**Current implementation status:**
`ARCHITECTURE REMEDIATION IMPLEMENTED — READY FOR FOCUSED FALSIFICATION #3`

### Baseline, authority, and bounded scope

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-15c`
- Branch: `phase/15c-frontend-navigation`
- Assigned `BASE_SHA` and current `HEAD`:
  `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Current `origin/main`: `895544db3341507dde5c2b210194c22e73e5a024`
- Latest main was not integrated, as explicitly required.
- Change classes: `ARCHITECTURE_REFACTOR`, `CI_TOOLING`, and `FRONTEND_UI`.
- Governing plan:
  `.ai-pipeline/001_planner/PHASE_15C_HTTP_FALLBACK_ARCHITECTURE_REMEDIATION.md`.

The exact installed Vite version remains **7.1.11** and `@vitejs/plugin-react`
remains **4.7.0**. The package manifest and lockfile were not changed by this
remediation. Exact-version installed source confirmed the required middleware order:
proxy, public, transform, raw-filesystem, and static handling; MPA HTML fallback;
returned `configureServer` hooks; Vite `indexHtmlMiddleware`; then Vite's final
not-found middleware.

### Architecture replacement

`vite.config.ts` now sets `appType: "mpa"`. The previous SPA-fallback architecture—
including the pre-Vite URL capture, request-header mutation, WeakMap, and custom 404
response owner—was retired in the same change. No compatibility path remains.

The single returned `configureServer` middleware runs after Vite's proxy/module/public/
static and MPA HTML resolution. Existing or MPA-resolved `.html` requests pass directly
to Vite. Only an unresolved, positively admitted document navigation is rewritten to
`/index.html`; Vite then reads and transforms the entry document, injects its development
runtime, owns GET/HEAD response behavior, and supplies the final 404 for every rejected
request. The middleware does not read a file, call `transformIndexHtml`, write an HTML
body, or emit a custom 404.

Vite's raw-filesystem middleware rewrites `request.url` before yielding for unresolved
`/@fs/**` paths. The post-hook therefore classifies Connect's server-provided
`request.originalUrl` while still using the current URL to preserve earlier MPA HTML
resolution. This was proved by an initial red real-server assertion and closes the
reserved-namespace escape without restoring the retired pre-hook capture architecture.

Positive admission now requires exact `GET` or `HEAD`; an absolute, unambiguous raw
path; at most three safe decoding rounds with valid `%HH` syntax and no encoded
separator/query/fragment/backslash/control/dot-segment/residual-percent ambiguity; no
API, resource, terminal-dot, semicolon/matrix, or reserved namespace in any canonical
form; a strictly parsed positive `text/html` range; and absent `Sec-Fetch-Dest` or
exactly `document`, `frame`, or `iframe`.

Malformed HTML parameters—including `text/html;q`—fail closed. Duplicate, empty,
negative, over-precision, and out-of-range qualities fail closed. Semicolon-bearing
paths are rejected and resource stems before a semicolon remain classified. Reserved
paths cover the installed Vite/React owners `/@vite`, `/@fs`, `/@id`,
`/@react-refresh`, `/src`, `/node_modules`, `/assets`, `/__open-in-editor`, and the
bounded `/__vite` prefix. No React Router route or business allowlist was copied into
Vite.

### Real-server evidence

`ViteHistoryFallback.test.ts` starts the actual configured Vite server against an
isolated fixture root and bounded local API backend. Raw Node HTTP requests preserve
malformed, encoded, semicolon, and dot-segment request targets for server-level
falsification.

Fresh assertions prove:

- `/` and `/index.html`, including HEAD, are served and transformed by Vite with the
  fixture marker, `/@vite/client`, React refresh preamble, and source-module entry;
- Phase 15C, wildcard, query-bearing, dotted-leaf, and dotted-parent navigation remains
  available only with positive document evidence;
- strict Accept and fetch-destination positive/negative matrices behave as specified;
- public/root static files and existing Vite/React/source modules retain truthful GET
  and HEAD responses;
- ordinary, encoded, double/triple-encoded, uppercase, query-bearing, terminal-dot,
  semicolon, document/data/WASM, asset, and non-navigation resource misses return 404
  without the SPA marker;
- `/dashboard%252525`, malformed percent input, encoded separators/query/fragment,
  matrix syntax, and dot-segment ambiguity return 404 without the SPA marker;
- unresolved reserved namespaces, including a raw-filesystem `/@fs/index.html`
  collision attempt, never become application HTML under adversarial document headers;
- bounded API responses remain JSON `401`/`404`, including encoded forms; and
- HEAD has an empty body, unsafe methods—including direct `/index.html` requests—
  remain 404/non-SPA, and OPTIONS remains Vite/server-owned with `204`.

The initial focused run was prevented before collection by the known Windows sandbox
`spawn EPERM` restriction. The authorized identical rerun started Vite and exposed one
real defect: unresolved `/@fs/**` was admitted after Vite mutated `request.url`. After
classification was bound to `request.originalUrl`, the complete focused matrix passed.
This red-to-green record is retained rather than represented as an environment-only
pass.

### Fresh verification

| Check | Result |
|---|---|
| Focused real-Vite fallback + Phase 15C navigation | PASS — 26/26 across 2 files |
| Historical F-01/F-04 regressions | PASS within the 25-test Phase 15C navigation suite |
| Full frontend suite | PASS — 181/181 across 9 files; historical non-failing React Router SSR warnings only |
| Frontend TypeScript | PASS |
| Frontend production build | PASS — Vite 7.1.11; 108 modules; JS 345.33 kB / gzip 100.62 kB; CSS 59.25 kB / gzip 12.65 kB |
| Architecture check | PASS |
| Project-state check | PASS |
| Secret scan | PASS |
| Windows lifecycle | NOT RERUN — accepted unchanged evidence remains 18/18 PASS in 266.225 seconds |
| Backend/contracts/physical Mongo | NOT APPLICABLE / NOT RERUN — no owning source changed |

The full frontend run re-executed the actual-server test; this is not helper-only
evidence. Server teardown left no listener on ports 5173 or 8000 and no
`.runtime/demo-processes.json` manifest. Lifecycle/root startup ownership was not
changed and no startup/root-health concern was observed, so the accepted lifecycle
evidence was not duplicated.

### Security, regression, and ownership review

The API proxy and backend still execute before fallback admission. The correction adds
no authorization or capability owner, credential handling, persistent browser cache,
PII/KYC logging, backend behavior, provider claim, business rule, mapping, schema, or
external integration. Malformed and ambiguous HTTP inputs fail closed. F-01 case-action
containment and F-04 stale-intake generation/session containment remain green; F-03
remains closed by the accepted lifecycle evidence.

The architecture self-check remains **PROCEED within the existing Vite development-
server owner**. React Router remains the sole client route owner, the backend remains
the API/RBAC owner, and Vite remains the module/static/HTML-transform/404 owner. ADR-001
remains **Proposed**. Production-host history fallback remains **UNVERIFIED — LATER
DEPLOYMENT-OWNER DEPENDENCY**.

Remediation-specific files are limited to:

- `apps/frontend/vite.config.ts`;
- `apps/frontend/ViteHistoryFallback.test.ts`; and
- `.ai-pipeline/reports/PHASE_15C_IMPLEMENTATION.md`.

The independent quality-gate and falsification reports remain immutable historical
evidence. No stage, commit, push, PR, merge, rebase, reset, stash, clean, branch switch,
sibling-worktree operation, latest-main integration, deployment, or next phase was
performed. This is implementer evidence only and does not self-issue PASS.
