# Phase 15C Independent Re-Quality-Gate Report — Frontend URL Navigation

## 1. Executive Result

**FINAL RE-QG VERDICT: FAIL**

**ARCHITECTURE REVIEW: REVISE**

The Phase 15C remediation closes F-01, F-03, and F-04. It also corrects the
originally demonstrated `/assets/**` miss: ordinary, encoded, nested, malformed, and
HEAD asset misses now return a real `404`, while a known asset, application routes,
the API proxy, and unsafe methods retain their intended handling.

Phase 15C is nevertheless not acceptable yet. Fresh probing of the actual configured
Vite development server found a remaining HIGH false-success in the same HTTP fallback
boundary: missing file/resource paths outside `/assets/**`, including JavaScript, CSS,
image, and font paths, return the SPA shell as `200 text/html`. That violates the
planner's explicit requirement that other static/file requests do not enter history
fallback and the accepted architecture invariant that the fallback never absorbs
static/file requests. The authored Vite integration test does not exercise this broader
surface.

This is one bounded infrastructure defect. No backend, workflow, provider, contract,
persistence, RBAC, cache-scope, business-rule, mapping, or Live-integration regression
was found.

## 2. Reviewed Baseline and Git State

- Worktree root:
  `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-15c`
- Branch: `phase/15c-frontend-navigation`
- Assigned `BASE_SHA`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- `HEAD`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- `origin/main`: `895544db3341507dde5c2b210194c22e73e5a024`
- Merge base: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Ahead/behind (`HEAD...origin/main`): `0 / 1`
- Staged files: none
- Implementation state: intentionally uncommitted
- Latest-main integration: deliberately not performed, as instructed
- Sibling worktrees: not inspected

Before this report, the exact Phase 15C working set was 18 modified tracked files and
9 untracked files.

Modified tracked files:

- `apps/frontend/package-lock.json`
- `apps/frontend/package.json`
- `apps/frontend/src/App.test.tsx`
- `apps/frontend/src/App.tsx`
- `apps/frontend/src/Dashboard.test.tsx`
- `apps/frontend/src/Phase14CaseManagementPerformance.test.tsx`
- `apps/frontend/src/Phase14_5AdminPolicy.test.tsx`
- `apps/frontend/src/UiV2Integration.test.tsx`
- `apps/frontend/src/main.tsx`
- `apps/frontend/src/pages/AuditTrail.tsx`
- `apps/frontend/src/pages/CaseDetail.tsx`
- `apps/frontend/src/pages/CaseQueue.tsx`
- `apps/frontend/src/pages/ClientDetail.tsx`
- `apps/frontend/src/pages/Dashboard.tsx`
- `apps/frontend/src/pages/OnboardedClients.tsx`
- `apps/frontend/vite.config.ts`
- `docs/ARCHITECTURE.md`
- `docs/decisions/DECISION_LOG.md`

Untracked implementation/planning/evidence files:

- `.ai-pipeline/001_planner/PHASE_15C_EXECUTION_ADDENDUM.md`
- `.ai-pipeline/001_planner/PHASE_15C_FRONTEND_NAVIGATION.md`
- `.ai-pipeline/reports/PHASE_15C_IMPLEMENTATION.md`
- `.ai-pipeline/reports/PHASE_15C_QUALITY_GATE.md`
- `apps/frontend/ViteHistoryFallback.test.ts`
- `apps/frontend/src/Phase15CNavigation.test.tsx`
- `apps/frontend/src/navigation.tsx`
- `apps/frontend/src/pages/RetainedIntakeRecovery.tsx`
- `docs/decisions/ADR-001_FRONTEND_URL_NAVIGATION.md`

This re-gate adds only
`.ai-pipeline/reports/PHASE_15C_RE_QUALITY_GATE.md`.

## 3. Phase Acceptance Checklist

| Acceptance surface | Result | Direct evidence |
|---|---|---|
| F-01 case identity isolation | **CLOSED** | `CaseDetail` binds action state and every relevant post-await publication/navigation effect to immutable generation, case ID, and actor user ID. Route/actor replacement clears dialogs, busy state, and error state. Four router-integrated adverse tests passed, including stale delete success/failure and Back/Forward dialog isolation. |
| F-02 `/assets/**` HTTP truth | **CLOSED FOR `/assets/**`** | Actual Vite tests and independent probes returned `404 text/plain` for ordinary, nested, query-bearing, encoded-slash, encoded-name, and malformed `/assets/**` misses; HEAD returned `404` with an empty body. A known CSS asset returned `200 text/css`. |
| Broader static/file HTTP truth | **FAIL** | Missing `/missing-script.js`, `/missing-style.css`, `/missing-image.png`, and `/missing-font.woff2` returned `200 text/html` and the SPA shell. See RQG-01. |
| F-03 Windows lifecycle | **CLOSED — OWNER EVIDENCE ACCEPTED** | The implementation report records one complete normal-CMD run: 18/18 PASS, `OK`, 266.225 seconds, with ports 5173/8000 free and manifest absent before and after. The lifecycle source/tests are unchanged from `HEAD`; no timeout or ownership logic changed. A duplicate four-minute run was not required by this task. |
| F-04 stale intake callbacks | **CLOSED** | Six deterministic deferred-promise tests passed for create/upload/completion after explicit reset and after logout/replacement login. The guards prevent stale route theft, state/error publication, follow-on mutation, old-user cache publication, and newer-journey overwrite. |
| Canonical route table | **PASS** | All required routes and wildcard are declared in `navigation.tsx`; direct entry, parent active links, Back/Forward, audit clearing, and safe root selection passed. |
| URL as sole navigation identity | **PASS** | Transient active-tab, selected-case, selected-client, audit-case, and test-only initial-tab owners are removed. No route loader/action or second navigation owner was added. |
| Deep link / refresh / login return | **PASS** | Direct route and refresh behavior, same-origin login return, and history traversal passed the focused suite and source review. |
| Retained intake recovery | **PASS** | `/new-onboarding/:caseId` reads backend case/document state only. It does not reconstruct `File` objects or initiate create/upload/complete/retry/resume. |
| Auth, cache, and backend ownership | **PASS** | `AuthProvider`, one QueryClient, user/case/team-scoped keys, AbortSignal forwarding, logout/401 clearing, and backend RBAC remain unchanged and authoritative. |
| Route-triggered mutation safety | **PASS** | The route-mount audit and full frontend suite passed; route entry/history/refresh initiates no business mutation. |
| Package scope | **PASS** | The only dependency addition is exact `react-router@7.18.4`; React/DOM 18.3.1, React Query 5.102.8, Vite 7.1.11, and TypeScript 5.9.3 remain unchanged. |
| Phase 15B and dev-tooling isolation | **PASS** | No Phase 15B backend/API/type/review behavior or dev-tooling Playwright harness was copied or integrated. |
| Broad regression | **PASS, with recorded baseline formatting debt** | Frontend 181/181 and backend 980 passed / 14 skipped; contracts, lint, mypy, secrets, architecture, project-state, typecheck, and build passed. Ruff format still reports 30 unchanged backend/script files. |
| Production-host fallback | **UNVERIFIED LATER DEPLOYMENT DEPENDENCY** | No production host exists in this reviewed tree. Local Vite evidence is not represented as production deployment evidence. |

## 4. Contract and Integration Findings

### RQG-01 — HIGH — Non-`/assets` file requests still receive false SPA success

- **Classification:** current Phase 15C infrastructure defect and false-success response.
- **Required contract:** the planner requires a real `404` for missing `/assets/**` and
  other static/file requests, and permits history fallback only for eligible
  application GET/HEAD requests. `docs/ARCHITECTURE.md` invariant 20 states that SPA
  history fallback never absorbs API, static/file, or unsafe-method requests.
- **Source evidence:** `apps/frontend/vite.config.ts:33` reserves only the exact
  `/assets` namespace. A missing path outside that namespace falls through to Vite's
  normal history behavior.
- **Fresh actual-server evidence:** with the repository Vite config on
  `127.0.0.1:5173`:
  - `GET /missing-script.js`, `Accept: */*` -> `200 text/html`;
  - `GET /missing-style.css`, `Accept: text/css,*/*;q=0.1` -> `200 text/html`;
  - `GET /missing-image.png`, browser-style image Accept -> `200 text/html`;
  - `GET /missing-font.woff2`, `Accept: */*` -> `200 text/html`;
  - the missing-JS response contained the application `<div id="root"></div>`.
- **Control evidence:** normal application routes returned the SPA shell; an app path
  with `Accept: application/json` returned `404`; an unsafe POST returned `404`; API
  proxy behavior remained non-SPA in the authored real-server test; all probed
  `/assets/**` variants returned `404`.
- **Test gap:** `apps/frontend/ViteHistoryFallback.test.ts:106` covers only
  `/assets/**` misses. It does not challenge other script/style/image/font misses.
- **Consequence:** a missing browser resource can be reported as successful HTML,
  producing false status/content semantics and MIME failures instead of a truthful
  miss. This is the same material class of HTTP-integrity failure as original F-02.
- **Required bounded remediation:** extend the development HTTP boundary so unresolved
  non-navigation resource/file requests cannot reach SPA fallback, while keeping
  legitimate application GET/HEAD navigation, `/api/**`, existing assets, and unsafe
  methods unchanged. Use explicit HTTP/request-destination semantics or another robust
  infrastructure rule; do not embed business routing in Vite or rely on a fragile
  arbitrary filename allowlist. Extend the actual-server test to cover missing
  JavaScript, stylesheet, image, font, encoded/malformed variants, HEAD, API, known
  assets, and normal application routes.

No external provider contract changed. ACRA remains Mock by default, the generic ACRA
sandbox seam remains Partial, IDP remains Local/Mock, ownership remains local
deterministic Decimal analysis, and GoldTier remains Mock only. No Live interoperability
claim is made.

## 5. Original Finding Reverification

### F-01 — closed

`CaseDetail` captures `{generation, caseId, actorUserId}` for each action
(`CaseDetail.tsx:49-105`), invalidates and clears local presentation on case/actor
replacement (`:129-135`), guards mutation/cache/error/busy/navigation publication
(`:160-190`), and renders dialogs only while their captured action remains current
(`:369-371`).

Fresh tests proved:

- A dialogs close on A -> B and do not retarget B;
- stale A delete success does not remove/navigate B;
- stale A delete failure does not surface on B;
- Back/Forward does not restore an old action dialog;
- B remains usable under its own current identity;
- no stale action issues a mutation scoped to B.

Actor replacement is also part of the identity predicate. The actual application keys
the authenticated App by user ID, and the full auth/intake replacement tests passed.

### F-02 — `/assets/**` portion closed; broader contract fails as RQG-01

The new post-static boundary correctly preserves known assets and converts unresolved
`/assets` or `/assets/**` requests to `404`. Independent probes confirmed encoded and
malformed forms are contained. The accepted broader static/file exclusion remains
incomplete outside that namespace.

### F-03 — closed by accepted manual evidence

The owner-supplied evidence is internally consistent and appended after remediation:
18 tests ran in 266.225 seconds and returned `OK`; pre/post ports were free and the
runtime manifest absent. `git diff` shows no change to:

- `tests/test_demo_lifecycle_windows.py`
- `scripts/demo_lifecycle.ps1`
- `scripts/start_demo_windows.bat`
- `scripts/stop_demo_windows.bat`
- `scripts/reset_demo_windows.bat`

No lifecycle timeout, ownership, cleanup, or process-management weakening was found.
The re-gate did not repeat the four-minute suite because the task explicitly permits
accepting this clean owner run when the evidence is consistent and lifecycle-owned
files are unchanged. Current closeout also found ports 5173/8000 free and no runtime
manifest.

### F-04 — closed

Six deferred-promise tests at `Phase15CNavigation.test.tsx:858-1049` cover stale
create, upload, and completion after explicit fresh reset and after authenticated
identity replacement. All passed. The current valid-generation intake test also passed,
showing one create, one upload, one completion, retained URL identity, and no replay
across route remounts.

## 6. Tester and Adversarial Findings

| Check | Fresh re-gate result |
|---|---|
| Focused Phase 15C navigation + Vite HTTP | PASS — 26/26 across 2 files |
| Focused Phase 15C + Phase 13/14/Dashboard | PASS — 57/57 across 5 files |
| Full frontend suite | PASS — 181/181 across 9 files |
| Frontend typecheck | PASS |
| Frontend build | PASS — 108 modules; JS 345.33 kB / gzip 100.62 kB; CSS 59.25 kB / gzip 12.65 kB; output directed to a temporary directory |
| Dependency inventory | PASS — exact React/DOM 18.3.1, React Query 5.102.8, React Router 7.18.4, Vite 7.1.11, TypeScript 5.9.3 |
| Full backend pytest | PASS — 980 passed, 14 skipped, 3 known Pydantic warnings |
| Ruff check | PASS |
| Ruff format check | BASELINE FAIL — 30 unchanged backend/script files would be reformatted; 121 already formatted |
| Mypy | PASS — 91 source files |
| Canonical contract unittest suite | PASS — 44/44 |
| Secret unit tests | PASS — 8/8 |
| `python scripts/check_secrets.py` | PASS |
| `python scripts/check_project_state.py` | PASS |
| `python scripts/check_architecture.py` | PASS |
| `git diff --check` | PASS; line-ending conversion warnings only |
| Owner manual Windows lifecycle | ACCEPTED — 18/18, 266.225 seconds, `OK` |
| Independent extra real-Vite static/file probes | **FAIL** — RQG-01 |
| Physical Mongo | NOT APPLICABLE — no persistence/schema/repository change |
| Pre-PR checker | NOT RUN — tree is intentionally uncommitted/dirty and latest-main integration is explicitly deferred |

The first focused Vitest attempt failed before collection with sandbox `spawn EPERM`
while esbuild tried to start. The identical command was rerun with process permission
and passed 26/26. This is environment evidence, not a code-test failure.

Non-failing React Router `useLayoutEffect` warnings remain in historical server-render
tests. They do not demonstrate a client runtime failure.

### POC regression result

The full backend suite and contract suite passed. No backend/provider/workflow file
changed. Accepted Registry -> Document -> Reconciliation -> Ownership -> Readiness ->
Mock GoldTier ordering, terminal states, failure call-stopping, no-replay behavior, and
Mock/Local/Partial/Dormant labels remain unchanged. The regression catalogue requires
no Phase 15C update.

## 7. Code and Architecture Review

**ARCHITECTURE REVIEW: REVISE**

- **Canonical navigation owner:** browser location plus `navigation.tsx`.
- **Existence check:** the retired transient App state and raw History API were not
  sufficient; declarative React Router is a proportionate focused owner.
- **Preserved owners:** `AuthProvider` for session lifecycle, TanStack Query for scoped
  server state, backend for RBAC/case existence/workflow, App for explicitly initiated
  live intake, and CaseDetail for local current-case actions.
- **Dependency direction:** routes/views continue to consume existing auth/query/API
  owners; no frontend-to-persistence or browser authorization owner was added.
- **Duplicate-owner check:** no second page/case navigation state, QueryClient, auth
  guard, router loader/action, or workflow owner was found.
- **Case action remediation:** local and cohesive; it does not alter backend business
  rules or create a shared state owner.
- **Vite responsibility:** infrastructure-only, but incomplete. Because the current
  implementation violates the accepted fallback invariant for non-`/assets` resource
  paths, the architecture cannot receive PROCEED yet.
- **ADR:** ADR-001 remains correctly `Proposed`; acceptance is not recommended until
  RQG-01 is remediated and independently re-gated.

## 8. Security Review

No new credential, authorization, KYC/PII, logging, persistence, provider, or browser
data-exposure defect was found.

- Backend capability/RBAC/team scope remains authoritative.
- Capability-aware route presentation does not grant access.
- Absent, inaccessible, and deleted cases retain the same sanitized `404` boundary.
- Login return uses the current same-origin URL; no open redirect or persisted return
  target was introduced.
- Logout, `401`, and identity replacement preserve cancellation and cache clearing.
- URLs contain only validated opaque case UUIDs, not credentials, tokens, UENs, legal
  names, filenames, document evidence, or private errors.
- No persistent browser case cache was introduced.
- Secret unit/scanner checks passed.

RQG-01 is an HTTP truth/integrity defect rather than an authorization bypass, but it is
still release-blocking because it produces false successful resource responses.

## 9. Required Fixes

1. Correct RQG-01 at the Vite development HTTP boundary without adding business logic
   or weakening application-route fallback.
2. Add actual-server regression coverage for non-`/assets` script, stylesheet, image,
   and font misses, including relevant encoded/malformed and HEAD variants.
3. Re-run the focused Vite/navigation suite, full frontend suite, typecheck, build,
   architecture/project-state/secret checks, and an independent re-quality gate.

F-01, F-03, and F-04 require no further remediation. Do not alter lifecycle tooling or
weaken its timeouts/ownership rules. Preserve the existing `/assets/**` fix.

## 10. Readiness

- **Phase 15C acceptance:** NOT ACCEPTED — `FAIL`
- **Owner-controlled commit readiness:** NOT READY
- **Latest-main integration readiness:** NOT READY; perform no integration until the
  bounded HTTP defect passes a new independent gate
- **Architecture:** REVISE
- **ADR-001 acceptance recommendation:** NOT YET
- **Phase 15B integration:** deliberately not reviewed or performed
- **Dev-tooling reconciliation:** when later authorized, preserve accepted Playwright
  dev-tooling changes during `package.json` / `package-lock.json` reconciliation; do
  not choose one lockfile side blindly
- **Production-host history fallback:** unverified later deployment-owner dependency
- **Live ACRA:** not proved; ACRA remains Mock by default and live binding remains
  blocked by sponsor/API authority and access
- **Real GoldTier/PingFed:** not ready/not in scope; GoldTier remains Mock only and
  real authentication/contract authority remains unresolved
- **Other sponsor dependencies:** Q-001 through Q-018 retain their recorded current
  statuses; Phase 15C does not resolve them

This verdict authorizes no remediation, stage, commit, push, PR, merge, rebase, reset,
stash, clean, branch switch, deployment, or next phase.

## 11. Review Boundary

The re-gate was read-only except for this report. It did not modify source, tests,
configuration, planner files, ADR-001, the implementation report, the original quality
gate, lifecycle tooling, Phase 15B content, or external systems. No commit, push, PR,
merge, rebase, reset, stash, clean, branch switch, latest-main integration, or
publication occurred.
