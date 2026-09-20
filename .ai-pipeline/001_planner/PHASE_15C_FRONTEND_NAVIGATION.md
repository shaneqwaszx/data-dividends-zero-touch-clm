# Phase 15C — Frontend URL Navigation

## Plan header

**Goal:** Replace transient tab/selected-case navigation with stable browser URLs while
preserving authentication, backend authorization, React Query isolation, onboarding
intake safety, and every existing business mutation boundary.

**Architecture:** The browser URL becomes the sole page and case navigation identity.
React Router declarative mode owns URL matching and browser history; `AuthProvider`
continues to own session lifecycle; TanStack Query continues to own scoped server state;
the backend remains the authorization and case-existence authority. No router loader,
router action, persistent browser cache, or duplicate workflow state owner is added.

**Tech stack:** React 18.3.1, TypeScript 5.9.3, Vite 7.1.11, TanStack Query 5.102.8,
and exact dependency `react-router@7.18.4` in declarative `BrowserRouter` mode.

**Baseline / authority refs:**

- branch `phase/15c-frontend-navigation`;
- `BASE_SHA`, planning `HEAD`, and `origin/main`:
  `a81e7da1c677f063408952e2ae1a1a2478afc22b`;
- clean tracked worktree at planning start;
- `AGENTS.md`, `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`, and
  `docs/DEVELOPMENT_WORKFLOW.md`;
- `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md`,
  `docs/contracts/MULTI_DOCUMENT_INTAKE_PROFILE.md`, and
  `docs/contracts/ZERO_TOUCH_AUTOMATION_POLICY.md`;
- `docs/decisions/DECISION_LOG.md` (especially D-040 and D-041) and
  `docs/sponsor-questions/OPEN_QUESTIONS.md` (especially Q-016);
- current frontend source/tests and the accepted UI V2 and Phase 14/14.5 cache gates;
- official React Router declarative-mode guidance and v7 compatibility guidance:
  <https://reactrouter.com/start/modes> and
  <https://reactrouter.com/upgrading/v7>.

**Compatibility boundary:** No backend route/model, provider, persistence schema,
business rule, source authority, workflow transition, case access policy, query-key
scope, cache duration, mutation retry, or provider-status label changes. Opaque case IDs
may appear in paths; credentials, session/CSRF values, tokens, evidence, document text,
filenames, UENs, legal names, and private error detail must not.

**TDD Route:**

- Mode: off (verified Aegis configuration).
- Decision: skipped.
- Strict authority: not applicable; neither the owner nor project requested strict TDD.
- Strict signals: navigation and session/cache behavior are shared behavior, so adverse
  regression coverage is mandatory even though strict RED/GREEN wording is not.
- Light eligibility: not eligible; this is cross-screen and architecture-sensitive.
- TDD-fit exception: none.
- Test posture: minimum implementation followed by focused navigation, stale-response,
  intake, auth, mutation-call-count, and live local fallback regressions.
- Verification: section 15.

**Verification summary:** Focused Phase 15C tests first; full frontend test/type/build;
architecture/project-state/security/secret/contract/lifecycle checks required by the
combined change classes; local Vite direct-route proof; independent security review,
POC regression, and quality gate. Physical Mongo is not required because no persistence
schema, adapter, CAS, index, startup, read/write, or restart semantic changes.

## 1. Scope and change classification

Implementation change classes:

- `FRONTEND_UI`: links, active navigation, route-specific empty/error pages;
- `FRONTEND_STATE_CACHE`: route-driven case switches, query cancellation, and stale
  response publication must remain safe;
- `AUTH_RBAC_SECURITY`: intended-destination restoration, capability presentation,
  non-enumerating case behavior, and URL data minimization;
- `ARCHITECTURE_REFACTOR`: a maintained routing library and canonical URL navigation
  owner replace the current tab/selected-ID owner.

This planner file is `DOCS_ONLY`. Implementation, remediation, independent quality gate,
and closeout remain distinct explicitly assigned runs.

In scope:

- stable routes for every current screen;
- direct URL entry, refresh, browser Back/Forward, and link semantics that permit a case
  to be opened in a new tab;
- safe login/session restoration at an intended internal route;
- safe unknown, unavailable, inaccessible, and deleted-case presentation;
- same-tab retained-intake URL identity and refresh-safe read-only recovery;
- route/cache race tests, including delayed Case A while navigating to Case B;
- the local SPA-history-fallback proof and a precise deployment-owner handoff contract.

Explicit non-goals:

- Phase 15B review/rework backend behavior or contracts;
- any backend API, DTO, persistence, provider, target, workflow, registry-refresh,
  document-processing, or approval change;
- navigation-triggered prefetch that changes current request behavior;
- router loaders/actions, React Router framework/data mode, SSR, service workers,
  offline support, or persistent browser storage;
- encoding list/search/team/presentation filters into URLs in this phase;
- production SSO, external return URLs, cross-origin redirects, or a `/login?returnTo=`
  protocol;
- a deployment-platform configuration not present in this repository;
- changes to lifecycle scripts, CI, Vite proxy infrastructure, or the dev-tooling
  worktree.

## 2. Verified current navigation ownership

Current ownership is entirely transient and concentrated in `apps/frontend/src/App.tsx`:

| Current state / callback | Current responsibility | Defect relative to Phase 15C |
|---|---|---|
| `activeTab: AppTab` | Chooses Dashboard, New onboarding, Cases, Onboarded, Audit, Policy, Users, or Teams | Refresh/direct entry cannot reproduce it; browser history does not observe it. |
| `selectedCaseId` | Switches Cases list to `CaseDetail` | No `/cases/:caseId`, no native new-tab link, and Back/Forward cannot restore selection. |
| `selectedClientId` | Switches Onboarded list to `ClientDetail` | Same transient identity problem. |
| `auditCaseId` | Seeds `AuditTrail` local state | URL and case-scoped audit can diverge after clear/back/forward. |
| `WorkspaceTabs` buttons | Calls state setters | Buttons have no link target and cannot provide normal browser link semantics. |
| `initialTab` test prop | Selects a page outside browser location | A second page identity exists solely for tests. |
| `intakeCaseRef` plus selected `File[]` | Safely retains the newly created case and same-tab upload progress | Correct in-memory mutation owner, but its retained case ID is absent from the URL. |
| `caseQueuePresentation` and per-page filters | Presentation inputs and server-query scope | These are not page/case navigation identity and may remain local/scoped in this phase. |

`apps/frontend/src/main.tsx` currently gates `App` behind `AuthProvider`, but no router is
mounted. `auth.tsx` already cancels and clears the in-memory QueryClient on restoration
failure, login replacement, logout, and 401. `caseQueries.ts` already keys detail,
documents, and ownership by authenticated user plus case ID and passes `AbortSignal` to
their GET functions. Those owners must be reused, not duplicated.

`App.tsx` is 2,295 lines and `App.test.tsx` is 1,690 lines at this baseline. Both exceed
the strong complexity-pressure threshold. Navigation is a new responsibility and must
not be added as another large inline state machine. `App.tsx` is limited to wiring and
retained onboarding state; new route ownership and new navigation tests go into focused
files.

## 3. Canonical route table

All paths are same-origin. Route parameters contain only an opaque case ID supplied by
the backend. `required capability` is a presentation guard over the server-authored
profile, never authorization.

| Route | Screen / identity | Required capability | Mount-time network behavior | History/link behavior |
|---|---|---|---|---|
| `/` | Capability-aware landing redirect | none | none | Replace with `/dashboard` for `CASE_ACCESS`; otherwise `/admin/users`, `/admin/teams`, then `/policy` according to available capability. |
| `/dashboard` | Dashboard | `CASE_ACCESS` | Existing user/team-scoped Dashboard GET only | Main-nav `NavLink`; case entries link to `/cases/:caseId`. |
| `/new-onboarding` | Blank or current live-tab onboarding journey | `CASE_ACCESS` | Existing execution-profile/team-option GETs only | If a live retained case exists in this tab, replace with `/new-onboarding/:caseId`; otherwise render the blank form. |
| `/new-onboarding/:caseId` | Same-screen live intake, or refresh recovery for retained intake | `CASE_ACCESS` | Existing safe case/document GETs for recovery; existing polling GET may remain | Set with `replace` immediately after create and before first upload. Never causes create/upload/complete/resume. |
| `/cases` | Authorized case queue | `CASE_ACCESS` | Existing scoped list GET | Main-nav link; presentation filters stay in current controlled state. |
| `/cases/:caseId` | Canonical case detail | `CASE_ACCESS` | Existing detail/documents/ownership GETs and existing read polling only | Case links are real anchors; direct entry, refresh, and new-tab work. |
| `/onboarded` | Completed Mock workflow list | `CASE_ACCESS` | Existing completed-list GET | Main-nav link. |
| `/onboarded/:caseId` | Existing client-detail presentation for one completed case | `CASE_ACCESS` | Existing case/documents/ownership GETs | Completed-case links are real anchors. Non-completed data must link to canonical `/cases/:caseId` rather than be presented as onboarded. |
| `/audit` | Authorized aggregate audit view | `CASE_ACCESS` | Existing authorized list/detail GET behavior | Main-nav link; action filter remains local presentation state. |
| `/audit/:caseId` | Case-scoped audit view | `CASE_ACCESS` | Existing safe case GET | Case identity comes only from the route parameter; Clear links to `/audit`. |
| `/policy` | Policy catalogue | `POLICY_VIEW` | Existing policy GET | Main-nav link. |
| `/admin/users` | User administration | `IDENTITY_ADMIN` | Existing profile/team GETs | Main-nav link. |
| `/admin/teams` | Team administration | `TEAM_ADMIN` | Existing team GET | Main-nav link. |
| `*` | Generic unknown/unavailable page | none | none | Keep the unknown URL, reveal no resource existence, and provide a link to the capability-aware landing path. |

There is no public `/login` return parameter. While authentication is loading or
anonymous, the browser remains on the requested same-origin path and renders the
existing loading/login view. Successful restoration or login reveals that route. If the
profile lacks the route's presentation capability, the generic unavailable page is
shown. Cross-team and absent case IDs still reach the backend only for a `CASE_ACCESS`
actor and retain the identical safe 404 projection.

## 4. Router decision and ADR requirement

### Decision

Use exact `react-router@7.18.4` with declarative `BrowserRouter`, `Routes`, `Route`,
`Navigate`, `NavLink`, `Link`, `useNavigate`, and `useParams` as needed. Import from
`react-router`; do not add the v7 compatibility re-export package
`react-router-dom`. Pin the exact version and update only the frontend lockfile through:

```powershell
npm.cmd --prefix apps/frontend install react-router@7.18.4 --save-exact
```

Reasons:

1. The current app needs matching, history, links, params, and active states, which is
   exactly React Router declarative mode.
2. The app already owns server data through TanStack Query and mutations through
   explicit handlers. Data/framework-mode loaders and actions would create overlapping
   owners and are prohibited in this phase.
3. The current React 18 baseline is compatible with maintained React Router v7. React
   Router v8 requires React 19 and Node 22.22+, so adopting v8 would force unrelated
   upgrades.
4. A custom `window.history`/`popstate` matcher would create repository-owned routing
   infrastructure, accessibility/link edge cases, and a larger testing/maintenance
   burden.
5. Hash routing is rejected because the approved routes are real pathnames and the
   deployment requirement explicitly calls for safe SPA history fallback.

### Architecture review result

`ARCHITECTURE REVIEW: PROCEED`, subject to the exact owner and retirement rules below.

- Existing owner candidates: `App.tsx` tab state and raw browser History.
- Existence conclusion: neither safely provides durable matching/link/history behavior;
  a focused `navigation.tsx` owner using a maintained library is lower entropy.
- Canonical owner after change: browser location plus `navigation.tsx` route/path map.
- Preserved owners: `AuthProvider`, QueryClient/query-key factories, backend RBAC,
  onboarding handlers, and backend workflow/persistence.
- Dependency direction: page links/shell -> navigation helpers/router -> page
  components; pages -> existing API/query owners. The router never imports backend or
  persistence code.
- Retirement: remove `activeTab`, `selectedCaseId`, `selectedClientId`, `auditCaseId`,
  `initialTab`, and their setter-based routing. Do not keep a feature flag or state
  fallback.
- Falsifier: any render branch still choosing a page or case by independent React state
  means the URL is not canonical and blocks completion.

This creates a framework/library and a canonical navigation owner, so it meets the ADR
criteria in `docs/DEVELOPMENT_WORKFLOW.md`. Implementation must create proposed
`docs/decisions/ADR-001_FRONTEND_URL_NAVIGATION.md` from the template, record the above
alternatives and SPA fallback consequence, and link it from
`docs/decisions/DECISION_LOG.md`. Independent acceptance—not this plan—may mark the ADR
Accepted.

## 5. Navigation owner and component boundary

Create `apps/frontend/src/navigation.tsx` as the only maintained path/route owner. It
must contain:

- literal route patterns and typed path builders for every row in section 3;
- `AppTab` and the visible-tab metadata/capability mapping now embedded in `App.tsx`;
- capability-aware default-path selection;
- `WorkspaceTabs` implemented with `NavLink` and correct parent-route active matching;
- a capability presentation wrapper that renders the same generic unavailable page and
  does not claim to authorize requests;
- route adapters that read opaque params and invoke the supplied page element/factory;
- the root redirect and wildcard unknown route.

Do not put API calls, QueryClient access, mutations, onboarding state, case status
interpretation, or auth transitions in this module. `App.tsx` supplies existing page
elements and callbacks and is reduced to wiring plus its existing onboarding journey
owner.

Create `apps/frontend/src/pages/RetainedIntakeRecovery.tsx` as a read-only recovery
projection. It consumes existing user/case-scoped query options, displays the retained
case ID, backend-authored status, and current document states, states that browser file
selections cannot be restored, and offers only links to the canonical case detail,
Cases, or a separately confirmed fresh-start action owned by `App.tsx`. It must not call
create, upload, retry, complete, resume, resolve, refresh-registry, or target-submit APIs.

## 6. Intake safety design

The intake sequence is fixed as follows:

1. `/new-onboarding` holds the existing selected `File[]` only in React memory.
2. The user explicitly submits the existing form. One create request is sent by the
   existing handler.
3. On the successful create response, retain the returned case ID in the existing
   `intakeCaseRef` and update the URL with
   `navigate(paths.retainedIntake(caseId), { replace: true })` before the first upload.
   This changes identity without leaving/unmounting the onboarding journey.
4. Continue the existing sequential upload and explicit intake-completion sequence.
   Existing successful-file and failed-document refs remain the only same-tab duplicate
   guards. Navigation does not call these handlers.
5. Navigating elsewhere does not unmount `App`'s live journey owner; an already
   user-initiated request may settle, but route changes start no new request.
6. Returning to New onboarding while a live case exists resolves to
   `/new-onboarding/:caseId`; `/new-onboarding` must not display that case under a
   case-less URL.
7. `Start another case` remains an explicit user action. It clears the current live
   journey through the existing reset owner and replaces the URL with
   `/new-onboarding`.
8. After a full refresh, no `File`, successful-file set, failed-document map, or live
   intake ownership is reconstructed. `/new-onboarding/:caseId` renders
   `RetainedIntakeRecovery` from GET data. It must not treat re-selected filenames as
   proof of the original package or bulk-upload them to the retained case.
9. Recovery actions are limited to what actual backend state supports. Existing case
   detail may expose its already-authorized targeted failed-document retry, resolution,
   or recovery controls after the user follows the case link. No new generic retry or
   inferred expected-document-count behavior is added.

This deliberately acknowledges that browser-selected `File` objects do not survive
refresh. A partial package whose missing original files cannot be proven remains a
retained backend case; the UI reports that truth instead of guessing or replaying.

## 7. Authentication, authorization, and URL safety

- Mount `BrowserRouter` outside `AuthProvider` in `main.tsx`; keep `AuthProvider` and its
  QueryClient exactly once.
- Keep the requested pathname/search/hash unchanged while session restoration or login
  is in progress. Do not put a return target in query parameters, storage, cookies, or
  auth payloads.
- Treat only the current same-origin router location as intended destination. No API
  accepts an external URL and no `window.location` assignment is introduced.
- On successful login, existing `acceptSession` still clears incompatible cache before
  rendering the retained route. On logout/401, existing cancellation and clearing run
  before the same route renders Login again.
- Navigation capability visibility comes only from the server-authored profile. It may
  hide/render screens but never grants access. Backend requests remain authoritative.
- Unknown and capability-unavailable routes share generic presentation. Case detail
  preserves the backend's identical 404 for absent and inaccessible IDs.
- Route builders encode only opaque IDs. No UEN, legal name, team name, filter text,
  priority, evidence, document metadata, error detail, credential, token, or CSRF value
  is added to URL or history state.
- Do not persist route-associated case data in localStorage, sessionStorage, IndexedDB,
  a service worker, or a shared HTTP cache.

## 8. React Query and race-safety interactions

No query-key factory, stale time, GC time, global retry, or mutation effect changes are
planned. Preserve:

- keys beginning with `auth`, authenticated `userId`, and exact case ID;
- Dashboard/list Director team-filter identity and server request parity;
- GET `AbortSignal` propagation for detail, documents, ownership, lists, and Dashboard;
- cache cancellation/clearing on logout, 401, identity replacement, and successful new
  login;
- mutation retry disabled;
- deletion cancellation and exact case-resource removal.

The route `/cases/:caseId` passes its current parameter directly to the existing query
option factories. In the required delayed-response test:

1. mount Case A and hold A detail/documents/ownership responses;
2. navigate to `/cases/B`;
3. assert A signals are aborted or A results remain confined to A keys;
4. resolve B and display only B;
5. resolve delayed A and assert no A identifier/evidence appears in B;
6. assert the cache contains no A data under B keys.

Existing polling generation/case binding remains in its current owner. A route mount may
perform existing reads/polling, but never a mutation. Do not add route prefetch in this
phase because it would change request timing and cancellation evidence.

## 9. Exact implementation files

### Create

| File | Exact responsibility |
|---|---|
| `apps/frontend/src/navigation.tsx` | Canonical patterns/builders, capability-aware defaults, `WorkspaceTabs`, route adapters, root redirect, and generic unknown/unavailable page. |
| `apps/frontend/src/pages/RetainedIntakeRecovery.tsx` | GET-only retained-case/document recovery view with explicit no-file-restoration copy and safe links. |
| `apps/frontend/src/Phase15CNavigation.test.tsx` | Focused direct-entry, history, link, auth, 404, no-mutation, intake, cache-race, and route-map regressions. Keep this coverage out of oversized historical test files. |
| `docs/decisions/ADR-001_FRONTEND_URL_NAVIGATION.md` | Proposed durable routing-library/URL-owner decision using the repository ADR template. |

### Modify

| File | Exact bounded change |
|---|---|
| `apps/frontend/package.json` | Add exact `react-router` dependency only. |
| `apps/frontend/package-lock.json` | Lockfile result of the exact install; no unrelated upgrade. |
| `apps/frontend/src/main.tsx` | Mount one `BrowserRouter` around the existing auth/application boundary; export the authenticated boundary only if focused tests require it. |
| `apps/frontend/src/App.tsx` | Remove transient page/case navigation state and `initialTab`; retain onboarding/presentation state; wire route elements and `useNavigate`; update the retained-intake URL on create; reset it only on explicit fresh start. Remove the unused manual `caseId`/`handleOpenCase` state path. |
| `apps/frontend/src/pages/Dashboard.tsx` | Replace case-open callbacks/buttons with canonical case `Link` targets while preserving query/team-filter behavior. |
| `apps/frontend/src/pages/CaseQueue.tsx` | Replace JS-only row/detail navigation with accessible canonical case links that support normal new-tab behavior; preserve filters, ordering, priority, and delete behavior. |
| `apps/frontend/src/pages/OnboardedClients.tsx` | Replace JS-only client navigation with canonical `/onboarded/:caseId` links; preserve completed-list query/filter/cache behavior. |
| `apps/frontend/src/pages/ClientDetail.tsx` | Preserve existing detail queries, but refuse to present a directly addressed non-`COMPLETED` case as onboarded; provide its canonical `/cases/:caseId` link without inventing access authority. |
| `apps/frontend/src/pages/AuditTrail.tsx` | Make route-supplied case ID the only audit case identity; Clear links to `/audit`; retain action filter as local presentation state. |
| `apps/frontend/src/App.test.tsx` | Replace `initialTab`/old `WorkspaceTabs` setup with `MemoryRouter` entries or focused component imports; do not add Phase 15C scenarios here. |
| `apps/frontend/src/Dashboard.test.tsx` | Supply router context and update `WorkspaceTabs` import/signature expectations. |
| `apps/frontend/src/UiV2Integration.test.tsx` | Supply router context and direct `/new-onboarding` entry for existing shell checks. |
| `apps/frontend/src/Phase14_5AdminPolicy.test.tsx` | Test capability-visible navigation through router links without changing admin/policy behavior. |
| `apps/frontend/src/Phase14CaseManagementPerformance.test.tsx` | Adapt removed list-open callback props and preserve N+1/cache/deletion assertions. |
| `docs/ARCHITECTURE.md` | Add frontend navigation canonical owner/invariant, declarative router boundary, retained-intake URL rule, and SPA fallback operational dependency; preserve all existing auth/cache/backend owners. |
| `docs/decisions/DECISION_LOG.md` | Link the proposed ADR with a project technical decision; do not label it sponsor-confirmed. |

### Explicit non-edits

Do not modify `apps/backend/**`, `apps/frontend/src/api.ts`,
`apps/frontend/src/types.ts`, `apps/frontend/src/caseQueries.ts`,
`apps/frontend/src/queryClient.tsx`, `apps/frontend/src/auth.tsx`, CI, lifecycle scripts,
`apps/frontend/vite.config.ts`, any provider/contract/persistence file, or the Phase 15B
worktree. If current main makes one of these edits necessary, stop and revise the plan
rather than expanding scope implicitly.

`docs/PROJECT_STATE.md` is not changed by implementation. A separately authorized
accepted-phase closeout may record Phase 15C after merge and verified current-main
inspection.

## 10. Implementation task sequence

### Task 1 — Record the navigation decision and install the exact dependency

**Files:** `docs/decisions/ADR-001_FRONTEND_URL_NAVIGATION.md`,
`docs/decisions/DECISION_LOG.md`, `apps/frontend/package.json`, and
`apps/frontend/package-lock.json`.

**Why / change necessity:** Native history plumbing is insufficient without building a
custom router. The minimum maintained dependency supplies matching/history/link
semantics while leaving server data and mutations in existing owners.

**Impact / compatibility:** React 18 remains unchanged; no React Router data/framework
mode; no unrelated package update.

**Steps:**

1. Capture the implementation TaskStartSnapshot and revalidate branch/base/clean state.
2. Create the Proposed ADR with the decision, alternatives, owner map, retirement,
   security, history-fallback consequence, verification, and revisit conditions.
3. Add its provisional project-technical entry to the decision log.
4. Run the exact package install command and audit the lockfile diff for only the router
   and its required transitive dependency.
5. Run `npm.cmd --prefix apps/frontend run typecheck` before routing source changes to
   prove the dependency alone did not perturb compilation.

### Task 2 — Establish the canonical route owner and auth boundary

**Files:** `apps/frontend/src/navigation.tsx`, `apps/frontend/src/main.tsx`, and
`apps/frontend/src/App.tsx`.

**Why / change necessity:** Page/case state must be replaced, not synchronized, or the
URL could contradict a second owner.

**Impact / compatibility:** Existing page components and `AuthProvider` remain; root
landing is capability-aware; unknown paths are inert.

**Steps:**

1. Add exact path constants/builders and route/capability table in `navigation.tsx`.
2. Implement `WorkspaceTabs` with `NavLink`, including Cases/Onboarded/Audit parent
   activation and dynamic retained-intake New-onboarding target.
3. Implement root redirect, param adapters, capability presentation guard, and wildcard
   page without API/mutation ownership.
4. Mount one `BrowserRouter` in `main.tsx` without moving or duplicating `AuthProvider`.
5. Replace `App.tsx` tab/selected-ID render branches with the route switch; remove the
   retired state/callbacks and `initialTab`.
6. Run the new route-map/direct-entry focused tests and typecheck.

### Task 3 — Convert case destinations to real links

**Files:** `Dashboard.tsx`, `CaseQueue.tsx`, `OnboardedClients.tsx`,
`ClientDetail.tsx`, `AuditTrail.tsx`, and the existing tests listed in section 9.

**Why / change necessity:** A callback-only button cannot expose an href for native
new-tab, copy-link, or browser history behavior.

**Impact / compatibility:** Queries, filters, table ordering, deletion, priority, team
scope, and view copy remain unchanged.

**Steps:**

1. Replace Dashboard case actions with canonical case `Link` elements.
2. Replace Case Queue JS-only detail opening with an accessible case link; retain
   delete-event propagation and keyboard access through the link itself.
3. Replace Onboarded client opening with an accessible completed-client link.
4. Keep Client Detail read-only on mount and, when direct entry returns a case whose
   backend-authored status is not `COMPLETED`, show a safe link to `/cases/:caseId`
   instead of presenting it as an onboarded client.
5. Bind Audit Trail case identity to the route param and make Clear a link to `/audit`.
6. Update historical tests only for changed component signatures/router context and
   preserve all existing behavioral assertions.
7. Run focused navigation plus Dashboard/Phase 14/14.5/UI V2 tests.

### Task 4 — Preserve live intake and add refresh-safe recovery

**Files:** `App.tsx`, `navigation.tsx`,
`pages/RetainedIntakeRecovery.tsx`, and `Phase15CNavigation.test.tsx`.

**Why / change necessity:** A retained case needs a durable URL before uploads begin,
but browser file handles and duplicate guards cannot safely be reconstructed after
refresh.

**Impact / compatibility:** Existing create/upload/complete order and call counts remain;
refresh is read-only; targeted case-detail recovery remains existing behavior.

**Steps:**

1. On create success, set `intakeCaseRef` and replace the URL with the retained case
   path before invoking document intake.
2. Keep the current form mounted for the matching live-tab retained case and redirect a
   case-less New-onboarding URL to that canonical case path.
3. Render `RetainedIntakeRecovery` when a route case ID has no matching live-tab intake
   owner, including after refresh.
4. Make explicit fresh-start reset state first and then replace the URL with the base
   New-onboarding path.
5. Prove one create, one upload per selected file, one complete call, retained ID on
   upload failure, no remount duplicate, and zero mutation calls on refresh/direct mount.
6. Prove no File object or sensitive intake value is serialized into URL/history/storage.

### Task 5 — Prove route/cache/auth adverse behavior

**Files:** `Phase15CNavigation.test.tsx` and only signature-adaptation edits in existing
tests.

**Why / change necessity:** Route correctness is incomplete if old-user data, Case A
data, or a mutation can publish under a new route.

**Impact / compatibility:** No query/cache implementation change is expected. A failing
test against current owners is a stop-and-diagnose signal, not permission to weaken
scope or keys.

**Steps:**

1. Cover every route and capability-aware root landing with `MemoryRouter`.
2. Cover direct case entry, refresh-equivalent remount, unknown route, capability-
   unavailable route, and identical absent/inaccessible case error presentation.
3. Cover normal link hrefs and modifier/new-tab eligibility without forcing a target.
4. Cover Back/Forward between list, Case A, Case B, Onboarded, and Audit.
5. Cover anonymous/restoring/authenticated transitions while the intended internal path
   remains unchanged, plus logout/401 cache clearing at that path.
6. Execute the delayed A -> B response scenario from section 8 for detail, documents,
   and ownership.
7. Spy on all unsafe methods and prove route mount/history/refresh/unknown paths emit no
   POST, PUT, PATCH, or DELETE and do not call create/upload/complete/resume/resolve.
8. Preserve and rerun existing Director filter, cross-user, deletion, polling-generation,
   and no-persistent-storage tests.

### Task 6 — Document architecture and verify local history fallback

**Files:** `docs/ARCHITECTURE.md`; no infrastructure file.

**Why / change necessity:** `BrowserRouter` requires an operational fallback contract,
and the new canonical owner must be visible in current architecture.

**Impact / compatibility:** Local Vite proof only. The absent production host remains an
explicit deployment-owner dependency.

**Steps:**

1. Update the frontend owner map/invariants and state that router navigation starts no
   mutation.
2. Start the existing supported local demo lifecycle without editing it.
3. Verify `/cases/<synthetic-opaque-id>`, `/new-onboarding`, `/policy`, and an unknown
   application path return the SPA entry document from the Vite frontend.
4. Verify `/api/does-not-exist` is handled by the API proxy/backend and is not HTML, and
   `/assets/does-not-exist.js` is a real static 404 rather than `index.html`.
5. Perform browser direct-entry/refresh/Back/Forward checks while authenticated and
   record the exact local environment.
6. Stop the supported lifecycle in a `finally` path and report residue status.
7. State `deployment-host verification not executed` unless an authorized real host was
   actually configured and tested by its owner.

## 11. Deployment fallback contract and dev-tooling handoff

No production web-server/CDN configuration exists in the inspected repository, and
dev-tooling owns infrastructure. Phase 15C therefore must not invent or edit an nginx,
CDN, reverse-proxy, lifecycle, CI, or hosting file.

The required deployment-owner rule is:

1. route `/api/**` to the backend (or return its normal API 404) before any SPA rule;
2. serve existing hashed static assets normally;
3. return a real 404 for missing `/assets/**` and other static/file requests;
4. apply the SPA fallback only to same-origin application `GET`/`HEAD` requests that
   accept HTML and did not match API/static handling;
5. return `index.html` for direct application paths such as `/cases/:caseId`;
6. never rewrite unsafe methods to `index.html`;
7. preserve the original browser pathname so `BrowserRouter` can match it.

Local Vite dev-server verification proves the repository development surface only. It
does not prove a future production host. If a host configuration lands on `origin/main`
before implementation, stop and coordinate with dev-tooling rather than editing it from
this phase.

## 12. Phase 15B overlap and concurrency fence

Phase 15B owns review/rework backend planning and implementation. Phase 15C owns only
frontend navigation, route identity, history, links, and navigation-shell wiring.

Rules:

- do not inspect, copy, modify, or merge the Phase 15B worktree;
- do not edit backend review/rework routes, models, services, persistence, or tests;
- do not change exception/reconciliation actions, allowed-action logic, resume behavior,
  review dialogs, status meanings, or backend error contracts;
- keep `CaseDetail` and `HomeOnboarding` business handlers in their existing owners and
  reach them through navigation callbacks/route elements;
- avoid `api.ts`, `types.ts`, `caseQueries.ts`, `queryClient.tsx`, and `auth.tsx`, which
  are shared integration surfaces and are not required by this plan;
- if Phase 15B later changes `App.tsx`, Case Detail props, review callbacks, or route-
  relevant backend behavior on `origin/main`, reconcile only after it is accepted and
  an owner authorizes latest-main integration; preserve 15B business intent and reapply
  the smallest URL-navigation wiring;
- an API/type/business-rule conflict that makes the route plan dependent on unaccepted
  Phase 15B behavior is a stop condition.

No Phase 15C claim may imply that review/rework has been changed, completed, approved,
or made autonomous.

## 13. Security and failure behavior

- Unknown route: generic page, zero API calls, zero existence disclosure.
- Capability-unavailable route: same generic page; no “forbidden case exists” wording.
- Absent/cross-team/deleted case: existing sanitized backend 404 through the detail
  query; no frontend distinction or enumeration.
- Successful deletion: existing deletion effect runs first; navigation then leaves the
  deleted detail. A later history visit may show the same safe 404 and must not resurrect
  cached data.
- Route mount: GET/read polling only. No create, upload, file retry, intake complete,
  workflow resume, review resolution, registry refresh, target submit, policy/admin
  mutation, priority update, or delete.
- Login intent: same-origin router location only; no open redirect surface.
- Browser history: opaque case IDs only. Never include payload fragments, names,
  filenames, UENs, evidence, errors, credentials, auth material, or private state.
- Errors: preserve current `ApiError` sanitization; no raw response/body/stack projection.
- Mock/Local/Partial/Dormant labels: unchanged and never presented as Live.

## 14. Focused test matrix

`Phase15CNavigation.test.tsx` must cover at least:

| ID | Scenario | Required evidence |
|---|---|---|
| P15C-NAV-01 | Each route direct entry | Correct screen and active nav; URL unchanged except root replace. |
| P15C-NAV-02 | Root by CASE_ACCESS and HR profiles | `/dashboard` or `/admin/users` safe default, no unauthorized fetch. |
| P15C-NAV-03 | Browser Back/Forward | Exact prior route/case restored without selected-ID state. |
| P15C-NAV-04 | Open Case link | Real same-origin `href=/cases/:caseId`; normal modifier/context new-tab semantics available. |
| P15C-NAV-05 | Unknown/capability-unavailable | Generic inert page and zero business/API mutation. |
| P15C-NAV-06 | Inaccessible, absent, and deleted case | Same sanitized safe 404 presentation; no cached resurrection. |
| P15C-NAV-07 | Login/restore at intended route | Login renders without URL rewrite; successful auth reveals the same safe internal route. |
| P15C-NAV-08 | Logout/401/identity replacement | Existing requests cancelled and cache cleared; retained route reveals no prior-user data. |
| P15C-NAV-09 | Case A -> B with delayed A | A is aborted/confined to A key; B never renders A. |
| P15C-NAV-10 | Create then upload | Retained URL set before upload; case ID/files retained in live tab; exact mutation counts. |
| P15C-NAV-11 | Intake remount/history | No recreate or duplicate upload/complete; live journey URL remains case-specific. |
| P15C-NAV-12 | Refresh retained intake | Actual backend case/doc state; no File restoration claim; zero unsafe method. |
| P15C-NAV-13 | Route-mount mutation audit | All routes/history transitions generate no unsafe request on mount. |
| P15C-NAV-14 | Audit case route | `/audit/:caseId` is sole case identity; Clear changes URL to `/audit`. |
| P15C-NAV-15 | Director/team cache regression | Existing user/team/filter query identities and request parity remain unchanged. |
| P15C-NAV-16 | Local fallback exclusions | app path -> index; `/api/**` not index; missing `/assets/**` not index. |

Use synthetic UUIDs and bounded safe fixture data only. Do not log or snapshot raw
document content, credentials, CSRF values, or private errors.

## 15. Verification commands and evidence

Run focused frontend evidence first:

```powershell
npm.cmd --prefix apps/frontend test -- --run src/Phase15CNavigation.test.tsx src/Phase14CaseManagementPerformance.test.tsx src/Phase13AuthPriority.test.tsx src/Dashboard.test.tsx
npm.cmd --prefix apps/frontend run typecheck
npm.cmd --prefix apps/frontend run build
```

Then the complete affected frontend suite:

```powershell
npm.cmd --prefix apps/frontend test -- --run
npm.cmd --prefix apps/frontend run typecheck
npm.cmd --prefix apps/frontend run build
```

Because `ARCHITECTURE_REFACTOR` and `AUTH_RBAC_SECURITY` apply, run the repository-wide
required evidence even though backend code is not expected to change:

```powershell
python -m pytest apps/backend/tests -p no:cacheprovider --tb=short
python -m ruff check apps/backend/app apps/backend/tests scripts
python -m ruff format --check apps/backend/app apps/backend/tests scripts
python -m mypy apps/backend/app
$env:PYTHONPATH = "$PWD\apps\backend;$PWD\tests\contract;$PWD"
python -m unittest discover -s tests/contract -p "test_*.py"
python -m unittest discover -s tests -p "test_demo_lifecycle_windows.py" -v
python -m unittest discover -s tests -p "test_check_secrets.py"
python scripts/check_secrets.py
python scripts/check_project_state.py
python scripts/check_architecture.py
git diff --check
```

Perform the supported local lifecycle/browser fallback checks from Task 6 and record
response status/content type plus browser behavior. Do not represent them as external
deployment verification.

Required review sequence after implementation:

1. `$integration-security-review` for auth intent, URL data minimization, capability
   presentation, 404 non-enumeration, upload refresh behavior, and error projection.
2. `$poc-regression-check` with no catalogue changes: navigation must not alter terminal
   statuses, workflow order, connector calls, call stopping, or Mock/Live claims.
3. Independent `$fyp-quality-gate` over source, tests, ADR/architecture, package diff,
   adverse navigation, local fallback evidence, and Phase 15B scope isolation.
4. Separate remediation and re-quality-gate runs if findings exist.

Physical Mongo is explicitly not applicable. Before later PR readiness, and only after
authorized latest-main integration plus a clean committed feature tree, run
`python scripts/pre_pr_check.py` and the repository pre-PR checklist. This plan does not
authorize commit, push, PR creation, merge, rebase, or main integration.

## 16. Acceptance criteria

Phase 15C implementation is ready for independent quality gate only when all are true:

1. `/cases`, `/new-onboarding`, and `/cases/:caseId` work by direct entry, local refresh,
   normal navigation, and browser Back/Forward.
2. Every route in section 3 has one canonical URL and the correct capability-visible
   navigation entry where applicable.
3. `activeTab`, selected case/client/audit identity, `initialTab`, and unused manual case
   open state are removed; no parallel page/case navigation state remains.
4. Case entries expose real hrefs and can be opened in a new tab without cloning app
   state or placing sensitive data in the URL.
5. Login/session restoration retains only a safe same-origin intended path and does not
   create an open redirect or persistent return-target store.
6. Unknown/capability-unavailable routes are inert and generic; absent, inaccessible,
   and deleted cases retain the backend's non-enumerating safe behavior.
7. Route mount/history/refresh causes no business mutation. Existing read/poll behavior
   remains in its current owner.
8. A newly created intake case is placed in `/new-onboarding/:caseId` before upload,
   stays on the onboarding screen, is not recreated on remount, and does not duplicate
   upload/complete calls.
9. After refresh, the retained case/document state is read from the backend, File
   selections are explicitly not restored, and no retry/resume/upload occurs without a
   separate user action already supported by the current case owner.
10. Delayed Case A responses never render under Case B; user, case, and Director team
    query isolation plus AbortSignal behavior remain proven.
11. Logout, 401, identity replacement, deletion, and cache clearing/cancellation
    regressions remain green; no persistent sensitive browser cache exists.
12. `react-router@7.18.4` is the only dependency addition; React/Vite/TanStack and other
    packages are not upgraded.
13. The Proposed ADR and architecture map accurately identify the URL/router owner,
    retired state, preserved auth/cache/backend owners, and deployment fallback need.
14. Local Vite direct-route fallback and API/static exclusions are executed and
    evidenced. Any real deployment host remains explicitly unverified unless actually
    tested by its owner.
15. Phase 15B business/backend behavior is untouched, all required checks pass, the diff
    is scoped, no secret/confidential artefact is newly tracked, and an independent QG
    issues the sole verdict.

## 17. Stop conditions and residual risks

Stop dependent implementation and return to planning when:

- `origin/main` or accepted Phase 15B changes invalidate the route/component/API owner
  assumptions;
- the branch/worktree is not the assigned clean Phase 15C checkout;
- direct routing would require a backend/API/schema/business-rule change;
- a router approach requires data loaders/actions or a second QueryClient/auth owner;
- refresh recovery would need guessing original files, expected package size, or retry
  idempotency not supplied by current backend state;
- absent and inaccessible case behavior can be distinguished;
- stale A can publish in B, auth cache clearing cannot be proved, or a route mount calls
  an unsafe method;
- production fallback work requires modifying dev-tooling-owned infrastructure without
  separate authority;
- an unrelated dependency/lockfile change appears;
- required evidence fails or is narrower than the claimed behavior.

Residual operational risk: `BrowserRouter` requires correct host fallback. This plan
fully specifies and locally tests the rule, but no production hosting surface exists in
the repository, so production direct-route support remains an explicit deployment-owner
prerequisite rather than a verified Phase 15C fact.

## 18. Planner checks and execution readiness

**Aegis Visibility:** Planning is necessary because URL identity replaces a shared
navigation owner and must not absorb authentication, cache, intake, or mutation
responsibility.

**BaselineUsageDraft:**

- Required baseline refs: constitution, current state/architecture/workflow, access and
  intake contracts, decisions/questions, current source/tests, latest relevant accepted
  UI/cache gates.
- Delivered context refs: owner Phase 15C brief and repository `AGENTS.md`.
- Acknowledged before plan refs: all required refs above.
- Cited in plan refs: header and sections 2–17.
- Missing refs: production deployment-host configuration (not present) and concurrent
  Phase 15B worktree (intentionally prohibited).
- Decision: continue with local fallback proof and explicit deployment-owner handoff.

**Requirement Ready Check:**

- Requirement source refs: owner Phase 15C request.
- Goals/scope refs: Objective, Architecture Requirements, Intake Safety, Cache/Auth
  Safety, Router Decision, Deployment, and Output sections of that request.
- User/scenario refs: direct entry, refresh, history, new tab, login return, unknown and
  inaccessible/deleted cases, intake refresh, and A -> B race.
- Requirement item refs: route table and sections 6–14.
- Acceptance/verification refs: sections 14–16.
- Open blocker questions: no blocker for planning; production host is explicitly outside
  this worktree and not represented as verified.
- Decision: ready.

**Change Necessity:** A documentation/config-only change cannot make browser history,
direct entry, refresh, or new-tab links work because current identity lives only in
React state. The minimum code boundary is one focused router owner, shell wiring, real
links, and read-only retained-intake recovery. Decision: code-change.

**Existence Check:**

- Proposed new surface: `navigation.tsx` plus maintained router dependency.
- Existing reuse candidates: `App.tsx` state, raw History API, AuthProvider, React Query.
- Why insufficient: App state/raw History do not provide durable matching/link semantics;
  AuthProvider and React Query have different canonical responsibilities.
- Creation proof: React Router declarative mode supplies only the missing browser
  navigation responsibility; existing auth/cache/data/mutation owners are reused.
- Entropy/retirement impact: one dependency and one focused owner; four transient
  navigation states and the test-only `initialTab` path retire with no fallback.
- Decision: add-with-proof.

**Architecture Integrity Lens:**

- Invariant: URL is the only page/case navigation identity; route entry is read-only.
- Canonical owners: URL/router for navigation, AuthProvider for session, React Query for
  server state, backend for authorization/workflow.
- Responsibility overlap: explicitly prohibited router loaders/actions, second cache,
  second auth guard, or retained selected-ID state.
- Higher-level simplification: real links replace callback-driven tab/detail selection.
- Retirement/falsifier: any remaining independent active page/case selection state or
  route-triggered mutation disproves completion.
- Verdict: proceed.

**Complexity Budget / Plan-Time Complexity Check:**

- Artifact class: Source Complexity and Test Complexity.
- Target pressure: `App.tsx` 2,295 lines and `App.test.tsx` 1,690 lines are over-budget;
  shared list pages are cohesive and smaller.
- Projected pressure: at-risk if routes/tests are added inline; within controlled bounds
  when the route owner, recovery page, and Phase 15C tests are separate and App changes
  are wiring/removal only.
- Better boundary: new `navigation.tsx`, `RetainedIntakeRecovery.tsx`, and
  `Phase15CNavigation.test.tsx`; no broad App refactor.
- Recommendation: extract new responsibility, make wiring-only App edits, and defer any
  unrelated App decomposition.

**Plan Pressure Test:** Owner/retirement and URL/auth/cache boundaries are explicit;
route, intake, race, security, and fallback evidence are executable; Phase 15B and
dev-tooling overlap is fenced. Pressure result: proceed.

**Execution Readiness View:**

- Intent Lock: URL-based frontend navigation only.
- Scope Fence: sections 1, 9 explicit non-edits, and 12.
- Baseline Lock: `a81e7da1c677f063408952e2ae1a1a2478afc22b`; revalidate before writes.
- Approved Behavior: section 3 route table and sections 6–8.
- Owner/Contract Constraints: URL/router, AuthProvider, React Query, and backend each
  retain exactly one stated responsibility.
- Compatibility Boundary: header plus sections 7, 8, 12, and 13.
- Retirement Boundary: transient navigation state and `initialTab` removed; presentation
  filters and live intake refs retained in their current owners.
- Task Batches: Tasks 1–6 in order; route owner precedes links/intake/tests.
- Test Obligations: sections 14–15.
- Review Gates: security review, POC regression, independent QG, and re-QG after any
  remediation.
- Drift/Rewind Rules: do not access Phase 15B worktree, do not rebase/reset/stash/clean,
  and stop on unreconcilable latest-main intent.
- Evidence Required Before Completion: green focused/full matrix, scoped dependency
  diff, no unsafe route calls, local fallback exclusion proof, no secrets, QG verdict.
- Advisory Boundary: this plan is execution guidance, not a `GateDecision`, sponsor
  approval, PR authority, or completion authority.

**Execution route:** inline coordinator. The tasks are sequential and converge on
`App.tsx`/navigation contracts; parallel source edits would create avoidable shared-file
conflicts. Implementation requires a separate explicit owner instruction. This planner
run stops after creating this file and performs no production edit, commit, push, PR,
merge, or next-phase work.
