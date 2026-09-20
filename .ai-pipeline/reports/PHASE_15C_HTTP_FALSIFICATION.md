# Phase 15C Adversarial HTTP Pre-QG Falsification

## 1. Verdict

**FAIL**

The remediation closes the previously reported ordinary non-`/assets` JavaScript,
stylesheet, image, font, manifest, data, case-variant, query-string, and single-encoded
resource misses. Genuine document navigation, existing Vite resources, API proxy
ownership, unsafe methods, and representative HEAD semantics also remain intact.

However, the actual configured Vite development server still returns the SPA shell as
`200 text/html` for materially resource-oriented requests that bypass the classifier:

1. an extensionless request with browser-fetch destination `empty`;
2. a double-encoded resource extension; and
3. a path ending in a dot.

An additional Accept-negotiation bypass returns HTML when `text/html` is explicitly
assigned quality zero. Any one of these false-success responses violates the Phase 15C
requirement that missing resource requests never be represented as successful SPA HTML.
The authored real-server test does not cover these forms.

No remediation was performed.

## 2. Baseline, Scope, and Boundary

- Worktree:
  `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-15c`
- Branch: `phase/15c-frontend-navigation`
- Assigned `BASE_SHA` and current `HEAD`:
  `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- `origin/main`: `895544db3341507dde5c2b210194c22e73e5a024`
- Merge base: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Ahead/behind (`HEAD...origin/main`): `0 / 1`
- Staged files: none
- Change classification reviewed: `FRONTEND_UI`, `ARCHITECTURE_REFACTOR`, and
  `DOCS_ONLY`, with regression evidence for the earlier Phase 15C
  `FRONTEND_STATE_CACHE` and `AUTH_RBAC_SECURITY` findings.
- Review mode: read-only except for this report.
- No latest-main integration, sibling-worktree inspection, implementation change,
  stage, commit, push, PR, merge, rebase, reset, stash, clean, deployment, or next phase
  occurred.

The current three-file remediation slice was reviewed in:

- `apps/frontend/vite.config.ts`
- `apps/frontend/ViteHistoryFallback.test.ts`
- `.ai-pipeline/reports/PHASE_15C_IMPLEMENTATION.md`

The complete existing Phase 15C working set was preserved. Before this report was
created it contained 18 modified tracked files and 10 untracked planner, implementation,
test, ADR, and gate files, with no staged files.

## 3. Findings

### HTTP-F-01 — HIGH — `Sec-Fetch-Dest: empty` is treated as document navigation

Exact live-server request:

```http
GET /resource-without-extension HTTP/1.1
Host: 127.0.0.1:5173
Accept: */*
Sec-Fetch-Dest: empty
```

Observed result:

| Status | Content-Type | SPA shell | Truthful for request class |
|---:|---|---|---|
| `200` | `text/html` | Yes (`<div id="root"></div>`) | **No** |

Control with the same request and `Sec-Fetch-Dest: image` returned
`404 text/plain; charset=utf-8`, not the SPA shell.

The same bypass was independently reproduced at `/.well-known/example` with
`Accept: */*` and `Sec-Fetch-Dest: empty`, which returned `200 text/html` and the SPA
shell. `empty` is the Fetch Metadata destination used by fetch/XHR-style requests; it
does not establish genuine browser document navigation. Treating it as eligible SPA
navigation allows extensionless resource/API-like misses to receive false success.

Relevant code path:

- `apps/frontend/vite.config.ts:19-22` lists resource destinations but omits `empty`.
- `apps/frontend/vite.config.ts:39-40` rejects only destinations present in that set.
- With no final extension, `apps/frontend/vite.config.ts:60` returns false and allows
  Vite's history rewrite to continue to `index.html`.

Test gap: `apps/frontend/ViteHistoryFallback.test.ts:173-178` checks an extensionless
request only with `Sec-Fetch-Dest: image`; it does not exercise `empty`.

### HTTP-F-02 — HIGH — one-pass decoding misses double-encoded resource extensions

Exact live-server request, sent with `curl --path-as-is` so the client did not normalize
the request target:

```http
GET /foo%252Ejs HTTP/1.1
Host: 127.0.0.1:5173
Accept: */*
```

Observed result:

| Status | Content-Type | SPA shell | Truthful for request class |
|---:|---|---|---|
| `200` | `text/html` | Yes (`<div id="root"></div>`) | **No** |

`GET /missing%252Ejs` and `GET /missing%25252Ejs` produced the same false-success
result. The single-encoded control `GET /foo%2Ejs` returned
`404 text/plain; charset=utf-8` and no SPA shell.

Relevant code path:

- `apps/frontend/vite.config.ts:78-84` decodes the raw path exactly once.
- `%252E` therefore becomes `%2E`, not `.`, and `resourceExtension()` sees no extension.
- With `Accept: */*`, `apps/frontend/vite.config.ts:60` classifies the request as
  navigation, allowing the SPA shell.

Test gap: the authored test covers an encoded dot and encoded slash, but not the
explicitly requested double-encoded-dot case.

### HTTP-F-03 — HIGH — a final trailing dot bypasses dotted-path rejection

Exact live-server request:

```http
GET /trailing-dot. HTTP/1.1
Host: 127.0.0.1:5173
Accept: */*
```

Observed result:

| Status | Content-Type | SPA shell | Truthful for request class |
|---:|---|---|---|
| `200` | `text/html` | Yes (`<div id="root"></div>`) | **No** |

`GET /double-dot..` also returned `200 text/html` with the SPA shell. This contradicts
the remediation's stated behavior that dotted non-HTML paths are treated as resources.

Relevant code path: `resourceExtension()` at `apps/frontend/vite.config.ts:31-35`
requires one or more non-dot characters after the final dot. A trailing dot therefore
produces `null`, and the request falls through as navigation at line 60.

The authored test has no trailing-dot case.

### HTTP-F-04 — MEDIUM — substring Accept parsing ignores `q=0`

Exact live-server request:

```http
GET /foo/file.xyz HTTP/1.1
Host: 127.0.0.1:5173
Accept: text/html;q=0, */*;q=1
Sec-Fetch-Dest: document
```

Observed result:

| Status | Content-Type | SPA shell | Truthful for negotiated representation |
|---:|---|---|---|
| `200` | `text/html` | Yes (`<div id="root"></div>`) | **No** |

The media range explicitly excludes HTML. The classifier nevertheless uses
`accept.includes("text/html")` at `apps/frontend/vite.config.ts:60`, so the unknown
dotted path is treated as an explicitly HTML-capable wildcard navigation. This is a
separate parsing flaw from the three path/destination bypasses above.

The authored test covers positive `Accept: text/html`, not quality values or explicit
HTML rejection.

## 4. Real-Server Adversarial Matrix

The server was started with the repository-supported command:

```powershell
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

The first sandboxed start failed before serving with `spawn EPERM` from esbuild. The
same command was rerun with process permission and Vite 7.1.11 started successfully on
`127.0.0.1:5173`. Requests below were made against that configured server, not only
against helper functions or mocked middleware.

### Resource misses

All of the following returned `404 text/plain; charset=utf-8`, never the SPA shell:

- scripts/modules/styles/data:
  `/missing.js`, `/missing.mjs`, `/missing.cjs`, `/missing.css`, `/missing.map`,
  `/missing.json`, `/missing.xml`, `/missing.txt`, `/missing.csv`;
- images:
  `/images/missing.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`, `.ico`, `.avif`;
- fonts:
  `/fonts/missing.woff`, `.woff2`, `.ttf`, `.otf`, `.eot`;
- conventional root resources:
  `/manifest.json`, `/site.webmanifest`, `/favicon.ico`;
- reserved assets:
  `/assets/missing.js`;
- odd extensions:
  `/foo/file.xyz`, `.bin`, `.dat`, `.unknownext` with no HTML intent;
- case variants:
  `/MISSING.JS`, `/foo/Missing.CSS`, `/fonts/MISSING.WOFF2`;
- query variants:
  `/missing.js?v=1`, `/foo/missing.css?theme=test`,
  `/images/missing.png?x=.html`;
- path shapes:
  `/foo/bar.baz`, `/foo.bar/baz.js`,
  `/path.with.multiple.dots/file.js`;
- single-encoded and malformed forms:
  `/missing%2Ejs`, `/images/missing%2Epng`, `/foo%2Ebar`,
  `/bad/%ZZ/missing.js`, `/assets/nested%2Fmissing.css`.

Malformed `/missing%2` was rejected with `404` and no SPA shell. Vite logged the
malformed URI rather than silently normalizing it.

The path-shape controls `/foo.bar/baz` and
`/path.with.multiple.dots/client-route` received the SPA shell because their final
segments are extensionless. That is not independently classified as a defect without
resource headers because those shapes may be wildcard client-navigation paths. The
explicit `Sec-Fetch-Dest: empty` cases in HTTP-F-01 remove that ambiguity.

### Header precedence

- `/missing.js` returned `404` for each tested Accept value:
  `*/*`, `text/html`, `text/css`, `application/javascript`, `application/json`,
  `image/*`, and `font/woff2`.
- `/missing.css` plus `Accept: text/html` and `Sec-Fetch-Dest: document` returned `404`;
  a known resource extension safely overrides contradictory document headers.
- `/foo/file.xyz` plus `Accept: text/html` and `Sec-Fetch-Dest: document` returned the
  SPA shell, preserving the intentionally permitted dotted wildcard document route.
- The same path plus `Sec-Fetch-Dest: script` returned `404`.
- `/resource-without-extension` plus `Sec-Fetch-Dest: image` returned `404` even with
  `Accept: text/html`.
- `/dashboard` plus `Accept: application/json` and `Sec-Fetch-Dest: empty` returned
  `404`, not HTML, because Vite's own history middleware did not rewrite the request.
- The `Sec-Fetch-Dest: empty` plus `Accept: */*` bypass is recorded in HTTP-F-01.
- The HTML quality-zero bypass is recorded in HTTP-F-04.

### Navigation preservation

Each required route returned `200 text/html` with the SPA shell when requested as a
document (`Accept: text/html`, `Sec-Fetch-Dest: document`):

- `/`
- `/dashboard`
- `/new-onboarding`
- `/new-onboarding/00000000-0000-4000-8000-00000000015a`
- `/cases`
- `/cases/00000000-0000-4000-8000-00000000015a`
- `/onboarded`
- `/onboarded/00000000-0000-4000-8000-00000000015a`
- `/audit`
- `/audit/00000000-0000-4000-8000-00000000015a`
- `/policy`
- `/admin/users`
- `/admin/teams`
- `/wildcard/client-route`
- dotted wildcard `/reports/quarter.v2`
- query-bearing `/dashboard?view=all`.

`HEAD /dashboard` and `HEAD /reports/quarter.v2` returned `200 text/html` with zero
response-body bytes. Navigation deep links were not broken by the remediation.

### API, methods, HEAD, and existing resources

- With no backend listener on port 8000, actual configured-server
  `GET /api/nonexistent` and `HEAD /api/nonexistent` returned Vite proxy
  `500 text/plain`, no SPA shell; the Vite log recorded proxy-owned
  `ECONNREFUSED 127.0.0.1:8000`. This proves the fallback did not intercept the API
  namespace, but is not a backend-response success claim.
- The focused real-server test supplied its bounded local backend and passed the stronger
  proxy controls: `/api/auth/me` returned `401 application/json` and
  `/api/missing.js` returned `404 application/json`, never SPA HTML.
- `POST /dashboard`, `PUT /cases/example`, `PATCH /audit/example`, and
  `DELETE /policy` returned `404` and no SPA shell.
- `HEAD /missing.js`, `/foo/missing.css`, and `/images/missing.png` returned
  `404 text/plain; charset=utf-8` with zero response-body bytes.
- Existing transformed resources `/src/styles.css`, `/src/styles.css?v=1`, and
  `/@vite/client` returned `200 text/javascript` with their real non-HTML bodies.
  Vite serves CSS source requests as transformed JavaScript modules in development;
  this is expected Vite behavior and proves the classifier is not blocking existing
  resources.

The server was stopped cleanly after probing. Final checks found ports 5173 and 8000
free and `.runtime/demo-processes.json` absent.

## 5. Closed-Finding Regression Check

- **F-01 remains closed.** The focused Phase 15C suite passed all 25 navigation,
  case-action, and intake tests, including the four routed CaseDetail action-isolation
  cases recorded by the latest re-QG.
- **F-04 remains closed.** The same focused suite passed the six deferred create,
  upload, and completion generation/reset/session-replacement cases recorded by the
  latest re-QG.
- **F-03 lifecycle was not rerun.** Lifecycle files and root/startup health behavior
  were unchanged by the current three-file remediation. The accepted owner evidence
  remains 18/18 PASS in 266.225 seconds. Fresh server cleanup independently confirmed
  ports 5173/8000 free and the runtime manifest absent.

No evidence from this falsification reopened F-01, F-03, or F-04.

## 6. Production Hosting Boundary

Production-host fallback equivalence is **out of scope for Phase 15C verification in
this repository**, not a defect in this falsification result:

- the planner explicitly excludes deployment-platform configuration not present in the
  repository;
- the execution addendum requires local Vite and production-host evidence to remain
  separate;
- ADR-001 calls production fallback an operational prerequisite owned by deployment;
  and
- `docs/ARCHITECTURE.md` states that local Vite behavior is development evidence only
  and no production hosting surface is currently verified.

No production-host behavior or equivalence is claimed.

## 7. Required Checks

| Check | Fresh result |
|---|---|
| Focused Vite + Phase 15C tests | PASS — 26/26 across 2 files |
| Actual configured Vite adversarial requests | **FAIL — HTTP-F-01 through HTTP-F-04** |
| Full frontend suite | PASS — 181/181 across 9 files; historical non-failing React Router SSR warnings remained |
| Frontend typecheck | PASS |
| Frontend build | PASS — 108 modules; output directed outside the repository to the system temporary directory; JS 345.33 kB / gzip 100.62 kB; CSS 59.25 kB / gzip 12.65 kB |
| `python scripts/check_architecture.py` | PASS |
| `python scripts/check_project_state.py` | PASS |
| `python scripts/check_secrets.py` | PASS |
| F-01/F-04 focused regression | PASS within the 25-test Phase 15C suite |
| F-03 lifecycle | NOT RERUN — accepted unchanged owner evidence is 18/18 PASS, 266.225s |
| Physical Mongo | NOT APPLICABLE |

The first focused Vitest attempt failed before collection with sandbox `spawn EPERM`
while esbuild started. The identical command was rerun with process permission and
passed 26/26. The first Vite server start had the same environment restriction; the
authorized rerun started successfully. These are execution-environment observations,
not code-test failures.

## 8. Consequence and Required Next Action

Phase 15C cannot receive a formal re-QG PASS while unresolved resource-oriented
requests can still be represented as successful SPA HTML. The required next action is
a bounded remediation of the existing Vite fallback classifier plus actual-server
regressions for:

- `Sec-Fetch-Dest: empty` with extensionless requests;
- double-encoded extensions;
- trailing-dot paths; and
- Accept quality values, especially explicit `text/html;q=0`.

The remediation must preserve the green controls above: declared and wildcard document
navigation, intentional dotted document navigation, existing resources, API proxy
ownership, unsafe-method rejection, and HEAD body semantics.

This FAIL does not authorize remediation, staging, commit, push, PR creation, merge,
latest-main integration, deployment, or the next phase.

## 9. Review Boundary and Git Status

The falsifier created only:

- `.ai-pipeline/reports/PHASE_15C_HTTP_FALSIFICATION.md`

No source, test, configuration, planner, ADR, implementation report, prior gate,
lifecycle file, backend file, dependency, or external system was modified. The reviewed
branch remains intentionally uncommitted and unstaged.
