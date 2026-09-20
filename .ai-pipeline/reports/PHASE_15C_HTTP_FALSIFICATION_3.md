# Phase 15C Adversarial HTTP Falsification — Round 3

## 1. Verdict

**PASS**

The Vite-first remediation correctly separates Vite-owned requests from unresolved
SPA document navigation on the actual configured Vite 7.1.11 server. Vite continues
to own the entry HTML, source modules, React refresh runtime, root static files, API
proxy, HTML transformation, and final 404. The returned Phase 15C middleware admits
only positively identified unresolved document navigation and does not return a body
or status itself.

All five round-two defects and all four round-one defects remain closed. Unresolved
reserved namespaces, resource-shaped paths, malformed/ambiguous paths, API requests,
and unsafe methods never returned the SPA shell. Normal, query-bearing, wildcard,
dotted-wildcard, and HEAD navigation remained functional. F-01 and F-04 also remain
closed in the focused Phase 15C suite.

Production-host fallback remains unverified and out of scope. This PASS applies only
to the reviewed local Vite development-server boundary and does not claim production
hosting equivalence.

## 2. Baseline, Scope, and Review Boundary

- Worktree:
  `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-15c`
- Branch: `phase/15c-frontend-navigation`
- Assigned `BASE_SHA`, merge base, and current `HEAD`:
  `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- `origin/main`: `895544db3341507dde5c2b210194c22e73e5a024`
- Branch state at review start: behind `origin/main` by one commit; latest main was
  deliberately not integrated.
- Staged files: none.
- Review classes: independent read-only `ARCHITECTURE_REFACTOR`, `CI_TOOLING`, and
  `FRONTEND_UI` HTTP falsification, plus focused regression evidence for the earlier
  Phase 15C F-01/F-04 findings.

The review read the Phase 15C planner, execution addendum, implementation report,
original and re-quality gates, both prior HTTP falsification reports, the Vite-first
remediation planner, current `vite.config.ts`, the actual-server test, the exact
installed Vite 7.1.11 source, architecture, decisions, sponsor questions, and required
repository workflow/skill material.

No implementation, test, configuration, planner, ADR, prior report, lifecycle file,
backend file, dependency, or external system was modified. This report is the sole
review-created artifact. No stage, commit, push, PR, merge, rebase, reset, stash,
clean, branch switch, sibling-worktree inspection, latest-main integration,
deployment, or next phase occurred.

## 3. Actual Middleware Ownership

### Configuration result

- `appType` is exactly `"mpa"`.
- `developmentNavigationFallback()` is registered as a Vite serve plugin.
- Its `configureServer` hook returns the middleware-registration callback; it does not
  install the admission middleware in the pre-Vite position.
- The middleware passes existing/MPA-resolved HTML onward, rewrites only positively
  admitted unresolved navigation to `/index.html`, and calls `next()` for every case.
- It does not read `index.html`, access the filesystem, call `transformIndexHtml`, set
  an HTML status/content type, write a response body, serve modules/static content, or
  contain a React Router route allowlist.
- The previous `appType: "spa"`, pre-Vite URL/header workaround, custom response
  owner, and duplicate fallback path are absent.

### Exact installed Vite 7.1.11 source result

The checked-in installed bundle at
`apps/frontend/node_modules/vite/dist/node/chunks/config.js` establishes this order:

1. configured plugin `configureServer` hooks are called and their returned callbacks
   retained;
2. proxy middleware;
3. public middleware;
4. transform middleware;
5. raw-filesystem middleware;
6. root static middleware;
7. MPA HTML-file resolution (`htmlFallbackMiddleware(..., false)`);
8. returned `configureServer` callbacks;
9. Vite `indexHtmlMiddleware`;
10. Vite `notFoundMiddleware`.

The exact source also confirms that `indexHtmlMiddleware` reads existing HTML and
calls `server.transformIndexHtml(...)`, while `notFoundMiddleware` sets `404` and ends
an empty response. Therefore a rejected request's empty `404` with no Content-Type is
Vite's truthful final miss, not a custom or disguised HTML response.

**Ownership conclusion:** the approved owner split is implemented. Vite handles
proxy/module/public/static/HTML transformation/final 404 first or last as appropriate;
the custom layer owns only positive admission of an otherwise unresolved navigation;
React Router remains the sole client-route owner after HTML loads.

## 4. Real-Server Method

Ports 5173 and 8000 were free and `.runtime/demo-processes.json` was absent before the
run. The actual repository server was started with:

```powershell
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

The first sandboxed attempt failed before listening with the known esbuild
`spawn EPERM` restriction. The identical command was rerun with process permission and
Vite 7.1.11 started on `127.0.0.1:5173` in 320 ms. Raw Node HTTP requests were used so
malformed, encoded, semicolon, and dot-segment request targets were not normalized by a
browser client. Each probe recorded method, raw path, relevant request headers, status,
Content-Type, response length, and whether the application shell marker was present.

Port 8000 intentionally remained free. Consequently the standalone live-server API
probes received proxy-owned `500 text/plain` connection failures. This proves the SPA
middleware did not absorb them but is not claimed as backend success. The focused
actual-server test separately started a bounded local API backend and proved the
stronger JSON `401`/`404` responses.

## 5. Vite-Owned Controls

| Method / raw path | Relevant headers | Status / Content-Type | SPA shell | Expected owner | Result |
|---|---|---|---|---|---|
| `GET /index.html` | `Accept: text/html`; `Sec-Fetch-Dest: document` | `200 text/html` | Yes, transformed entry | VITE | PASS |
| `HEAD /index.html` | same | `200 text/html`, 0 body bytes | No body | VITE | PASS |
| `GET /@vite/client` | `Accept: */*`; `Sec-Fetch-Dest: script` | `200 text/javascript` | No | VITE | PASS |
| `GET /@react-refresh` | same | `200 text/javascript` | No | VITE | PASS |
| `GET /src/main.tsx` | same | `200 text/javascript` | No | VITE | PASS |
| `HEAD /src/main.tsx` | same | `200 text/javascript`, 0 body bytes | No | VITE | PASS |
| `GET /src/styles.css` | same | `200 text/javascript` transformed style module | No | VITE | PASS |
| `GET /package.json` | `Accept: application/json`; `Sec-Fetch-Dest: empty` | `200 application/json` | No | VITE root static | PASS |

The transformed `/index.html` contained `/@vite/client`, `/@react-refresh`, and the
actual `/src/main.tsx` entry. The application has no `apps/frontend/public` directory,
so there is no genuine public-directory asset to invent as a control; the real root
static JSON and transformed source/style resources above exercise the available static
and module surfaces.

When contradictory document headers were sent to internal resource paths,
`/src/main.tsx` and `/src/styles.css` remained non-SPA Vite responses, while
`/@vite/client`, `/@vite/env`, and `/@react-refresh` returned truthful `404` rather
than SPA HTML. With the request headers actually emitted for scripts, those internal
resources returned their normal JavaScript responses as shown above.

## 6. Unresolved Reserved Namespaces

Each request below used `GET`, `Accept: text/html`, and
`Sec-Fetch-Dest: document`. Every response was `404`, had no HTML Content-Type or body,
and contained no SPA marker.

| Raw path | Expected owner | Result |
|---|---|---|
| `/@vite/does-not-exist` | TRUTHFUL MISS | PASS |
| `/@fs/does-not-exist` | TRUTHFUL MISS | PASS |
| `/@id/__x00__missing` | TRUTHFUL MISS | PASS |
| `/@react-refresh/does-not-exist` | TRUTHFUL MISS | PASS |
| `/src/does-not-exist.js` | TRUTHFUL MISS | PASS |
| `/node_modules/does-not-exist/index.js` | TRUTHFUL MISS | PASS |
| `/__vite_missing` | TRUTHFUL MISS | PASS |

Encoded namespace controls such as `/@vite%2Fdoes-not-exist`,
`/%40vite/does-not-exist`, `/%2540vite/does-not-exist`,
`/src%2Fdoes-not-exist.js`, and `/assets%2Fdoes-not-exist.js` also returned truthful
non-SPA `404` responses.

## 7. Historical Defect Replay

### Round two — all five closed

| Prior defect | Exact real-server replay | Observed result | Owner | Result |
|---|---|---|---|---|
| A — semicolon suffix | `GET /missing.js;v=1`, HTML/document | `404`, no Content-Type/body, no shell | TRUTHFUL MISS | CLOSED |
| B — malformed q | `GET /dashboard`, `Accept: text/html;q`, document | `404`, no shell | TRUTHFUL MISS | CLOSED |
| C — decode-bound residue | `GET /dashboard%252525`, HTML/document | `404`, no shell | TRUTHFUL MISS | CLOSED |
| D — real index | `GET` and `HEAD /index.html`, HTML/document | `200 text/html`; HEAD empty | VITE | CLOSED |
| E — Vite internal/virtual | genuine internal script requests succeeded; unresolved `/@id/**`, `/@vite/**`, `/@fs/**`, `/src/**` returned `404` even with document headers | never SPA | VITE / TRUTHFUL MISS | CLOSED |

### Round one — all four closed

| Prior defect | Exact real-server replay | Observed result | Result |
|---|---|---|---|
| extensionless + `Sec-Fetch-Dest: empty` | `GET /extensionless-resource`, `Accept: */*` | `404`, no shell | CLOSED |
| double-encoded resource suffix | `GET /foo%252Ejs`, HTML/document | `404`, no shell | CLOSED |
| trailing dot | `GET /trailing-dot.`, HTML/document | `404`, no shell | CLOSED |
| explicit HTML quality zero | `GET /dashboard`, `Accept: text/html;q=0`, document | `404`, no shell | CLOSED |

## 8. New Boundary Attack Results

### Path/header precedence matrix

The full representative matrix combined `/missing.js`, `/unknown.extension`,
`/extensionless-resource`, and `/dashboard` with:

- `Accept: text/html`, `text/html;q=0`, `text/html;q`, `*/*`, and
  `application/json`; and
- `Sec-Fetch-Dest: document`, `empty`, `script`, and absent.

Results:

- `/missing.js` returned `404` in every combination. Positive document headers did not
  override a recognized resource path.
- `/dashboard` returned SPA HTML only for positive `text/html` with a document or
  absent destination. Zero/malformed/wildcard/non-HTML Accept and non-document
  destinations returned `404`.
- `/unknown.extension` returned SPA HTML only for positive `text/html` with document
  or absent destination; wildcard/non-HTML Accept or `empty`/`script` returned `404`.
- `/extensionless-resource` followed the same rule.

The latter two positive results are not false success. The approved contract
intentionally supports wildcard and dotted-wildcard client navigation without copying
the React Router route table into Vite. An unknown suffix or extensionless name is not
resource authority by itself; explicit positive HTML permission plus a compatible or
absent navigation destination admits it. A single destination signal, wildcard Accept,
or non-HTML Accept never admitted it.

### Accept parsing

Positive controls `TEXT/HTML`, `Text/Html;Q=0.8`, mixed media lists with a positive
HTML range, and a later positive HTML range after `q=0` returned SPA HTML. The following
returned truthful `404` responses: missing `=`, empty q, `.5`, `000`, negative,
out-of-range, over-precision, duplicate q, `q=0`, wildcard-only, non-HTML-only,
`text/html;q=0, */*;q=1`, and unsupported quoted parameter syntax. This matches the
strict/fail-closed parser contract.

### Canonicalization and malformed input

Every path below used HTML/document headers and returned `404` with no SPA marker:

- resource encodings: `/foo%2Ejs`, `/foo%252Ejs`, `/foo%25252Ejs`, and one additional
  beyond-bound `/foo%2525252Ejs` control;
- percent residue: `/dashboard%25`, `/dashboard%2525`, `/dashboard%252525`, and
  `/dashboard%25252525`;
- malformed encoding: `/bad/%ZZ/path`, `/malformed%`, and `/dashboard%2`;
- encoded ambiguity: `/foo%2Fbar`, `/foo%252Fbar`, `/foo%5Cbar`, `/foo%255Cbar`,
  `/foo%3Fbar`, `/foo%253Fbar`, and `/foo%23bar`;
- controls/NUL: `/foo%00bar` and `/foo%2500bar`;
- dot segments: `/foo/%2E%2E/bar` and `/foo/%252E%252E/bar`.

`/foo%2E%2E/bar` returned SPA HTML because it decodes to `/foo../bar`, not a `.` or
`..` path segment. That is an intentional dotted-parent wildcard path, not path
traversal or malformed residual state.

### Semicolon behavior

`/missing.js;v=1`, `/foo.css;theme=dark`, `/path/file.png;x=1`,
`/extensionless;matrix=1`, and single/double/triple encoded semicolon variants all
returned truthful non-SPA `404` responses. Phase 15C defines no legitimate semicolon
client route, so none was invented for a positive control.

## 9. SPA Navigation Preservation

Every request below used `GET`, `Accept: text/html`, and
`Sec-Fetch-Dest: document` and returned `200 text/html` with the transformed application
shell:

- `/`, `/dashboard`, `/new-onboarding`, `/new-onboarding/example`;
- `/cases`, `/cases/example`;
- `/onboarded`, `/onboarded/example`;
- `/audit`, `/audit/example`;
- `/policy`, `/admin/users`, `/admin/teams`;
- query-bearing `/dashboard?view=all`;
- wildcard `/wildcard/client-navigation`;
- dotted wildcard `/reports/quarter.v2`; and
- dotted parent `/customer.v2/profile`.

`HEAD /dashboard` and `HEAD /reports/quarter.v2` returned `200 text/html` with zero body
bytes. Direct deep-link and wildcard document behavior therefore remained available;
truthful resource rejection did not break valid navigation.

## 10. API and Method Boundaries

### API

With port 8000 deliberately unavailable, the actual configured Vite proxy owned these
requests and returned `500 text/plain`, zero body bytes, and no SPA marker:

- `GET /api/nonexistent`;
- `HEAD /api/nonexistent`;
- `GET /api/foo.js`;
- `GET /api/foo%252Ejs`; and
- `GET /api/auth/me`.

Encoded `/api%2Fnonexistent` and `/api%252Fnonexistent` also reached the proxy and did
not become SPA HTML. The authored actual-server integration test ran a bounded backend
and freshly passed JSON `401` for `/api/auth/me` plus JSON `404` for missing API paths,
including encoded/resource variants. No API request returned application HTML.

### Methods

| Request | Observed result | Owner | Result |
|---|---|---|---|
| `POST /dashboard` | `404`, empty, no shell | TRUTHFUL MISS | PASS |
| `PUT /cases/example` | `404`, empty, no shell | TRUTHFUL MISS | PASS |
| `PATCH /audit/example` | `404`, empty, no shell | TRUTHFUL MISS | PASS |
| `DELETE /policy` | `404`, empty, no shell | TRUTHFUL MISS | PASS |
| `OPTIONS /dashboard` | `204`, empty, no shell | VITE/server | PASS |

POST/PUT/PATCH/DELETE controls against `/index.html`, `/@vite/client`, and
`/missing.js` also returned `404` and never HTML. OPTIONS returned `204` with no body.

## 11. Response Truth

- Rejected Vite-owned misses returned non-success `404`, no HTML Content-Type, an empty
  body, and no SPA marker. This exactly matches the reviewed Vite 7.1.11 final
  `notFoundMiddleware`; it is not a disguised `200 text/html`.
- Proxy-unavailable API responses were `500 text/plain`, not HTML.
- HEAD classification matched GET and returned zero body bytes for both accepted HTML
  and rejected resource/reserved/malformed requests.
- Existing resources retained truthful non-HTML types under their actual request
  headers.
- No rejected request in the adversarial matrices returned `200 text/html`.

## 12. Closed Phase 15C Findings

- **F-01 remains closed.** The router-integrated CaseDetail generation/case/actor
  action-isolation tests passed. Stale Case A dialog, success, failure, and history
  effects cannot migrate to Case B.
- **F-04 remains closed.** The six deferred create/upload/completion tests across
  explicit fresh reset and logout/replacement login passed.
- These checks are part of the fresh 25/25 `Phase15CNavigation.test.tsx` result.
- The accepted F-03 Windows lifecycle evidence remains 18/18 PASS in 266.225 seconds.
  It was not rerun because no lifecycle/startup/root-health owner changed and the real
  server started and served `/` successfully.

## 13. Verification Results

| Check | Fresh round-three result |
|---|---|
| Actual configured Vite 7.1.11 server, raw adversarial probes | PASS — all required historical, reserved, malformed, API, method, response-truth, and navigation controls behaved as specified |
| Focused Vite fallback + Phase 15C navigation | PASS — 26/26 across 2 files |
| F-01/F-04 regressions | PASS within the 25-test Phase 15C navigation suite |
| Full frontend suite | PASS — 181/181 across 9 files; historical non-failing React Router SSR warnings only |
| Frontend typecheck | PASS |
| Frontend production build | PASS — Vite 7.1.11, 108 modules; JS 345.33 kB / gzip 100.62 kB; CSS 59.25 kB / gzip 12.65 kB; output used and removed from a verified temporary directory |
| `python scripts/check_architecture.py` | PASS |
| `python scripts/check_project_state.py` | PASS |
| `python scripts/check_secrets.py` | PASS |
| `git diff --check` before report | PASS; line-ending conversion warnings only |
| Phase 15C Windows lifecycle | NOT RERUN — accepted unchanged evidence remains 18/18 PASS in 266.225 seconds |
| Backend/contracts/physical Mongo | NOT APPLICABLE / NOT RERUN — no owning source changed |

The initial sandboxed Vite start and focused Vitest attempt failed before execution
with esbuild `spawn EPERM`. Each identical command passed after the required process
permission was granted. These were environment restrictions, not test failures, and
are retained here rather than omitted.

## 14. Production Hosting and Readiness

Production hosting fallback remains **UNVERIFIED / OUT OF SCOPE**. No production
server/CDN configuration exists in this repository, and no local Vite result is
represented as production-host evidence. This truthful limitation is not a Phase 15C
defect.

- **Round-three HTTP falsification:** PASS.
- **Vite-first local development ownership boundary:** verified.
- **All nine historical HTTP falsifier defects:** closed.
- **Valid SPA navigation and F-01/F-04:** verified.
- **Production-host fallback:** unverified later deployment-owner dependency.
- **Live ACRA / real GoldTier/PingFed:** unchanged and not proved; provider truth
  remains Mock/Local/Partial/Dormant exactly as recorded.

This PASS supplies the requested focused falsification evidence. It does not by itself
accept ADR-001, authorize a commit/PR/integration/deployment, or start another phase.

## 15. Git and Cleanup Status

The branch remains intentionally uncommitted and unstaged. Existing Phase 15C modified
and untracked implementation/history artifacts were preserved. The only file created
by this review is:

- `.ai-pipeline/reports/PHASE_15C_HTTP_FALSIFICATION_3.md`

The real server was stopped after probing. Final cleanup verification is recorded after
report creation: port 5173 free, port 8000 free, and runtime manifest absent.
