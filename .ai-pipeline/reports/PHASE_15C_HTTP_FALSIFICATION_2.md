# Phase 15C Adversarial HTTP Falsification — Round 2

## 1. Verdict

**FAIL**

The second remediation closes all four first-round bypasses on the actual configured
Vite 7.1.11 server. It also preserves the declared application routes, representative
existing transformed resources, the API proxy boundary, unsafe-method exclusion, and
the previously closed F-01/F-04 frontend regressions.

The positive-admission classifier is nevertheless still falsifiable. Fresh real-server
probing found:

1. resource paths with semicolon/path-parameter suffixes receive the SPA shell;
2. a malformed `q` parameter without `=` is treated as positive HTML acceptance;
3. a percent sequence that becomes malformed exactly at the decode bound is admitted;
4. the real existing `/index.html` entry resource is blocked by the classifier; and
5. reserved Vite internal/virtual-module request paths can be converted into SPA HTML
   by document headers.

The first three are false-success paths (`200 text/html` plus the application shell).
The fourth violates the requirement that existing resources remain available. Any one
of them prevents PASS. No remediation was performed.

## 2. Baseline, Scope, and Review Boundary

- Worktree:
  `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-15c`
- Branch: `phase/15c-frontend-navigation`
- Assigned `BASE_SHA` and current `HEAD`:
  `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Local `main`: `5ebf458ac22ce1e072145be7b3e941df5abbbe0e`
- `origin/main`: `895544db3341507dde5c2b210194c22e73e5a024`
- Merge base reported by `scripts/dev_context.py`:
  `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Branch state: behind `origin/main` by one commit; latest main was deliberately not
  integrated.
- Staged files: none.
- Review classification: independent read-only `FRONTEND_UI` / `CI_TOOLING` HTTP
  security-boundary falsification, with focused `FRONTEND_STATE_CACHE` regression.
- Sole reviewer-created artifact:
  `.ai-pipeline/reports/PHASE_15C_HTTP_FALSIFICATION_2.md`.

The existing Phase 15C working set was preserved. No implementation, test,
configuration, planner, ADR, previous report, lifecycle file, dependency, backend,
contract, provider, or external system was modified. No stage, commit, push, PR,
merge, rebase, reset, stash, clean, branch switch, sibling-worktree inspection,
latest-main integration, deployment, or next phase occurred.

Before the real-server run, ports 5173 and 8000 were free and
`.runtime/demo-processes.json` was absent. The first sandboxed server start failed
before listening with esbuild `spawn EPERM`; the identical command was rerun with the
required process permission:

```powershell
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

The configured Vite server started on `127.0.0.1:5173`. It was stopped cleanly after
the probes. Final checks again found ports 5173 and 8000 free and the runtime manifest
absent.

## 3. Findings

### HTTP2-F-01 — HIGH — Path-parameter resource suffix bypass

Exact real-server request:

```http
GET /missing.js;v=1 HTTP/1.1
Host: 127.0.0.1:5173
Accept: text/html
Sec-Fetch-Dest: document
```

| Status | Content-Type | SPA shell | Expected classification |
|---:|---|---|---|
| `200` | `text/html` | Yes (`<div id="root"></div>`) | Missing JavaScript resource; no SPA fallback |

The encoded form `/missing.js%3Bv=1` and `/missing.css;anything` produced the same
false `200 text/html` SPA response. Query controls `/missing.js?route=/dashboard` and
`/missing.css?x=.html` correctly returned `404`, so this is specifically a pathname
classification bypass rather than query contamination.

`resourceExtension()` at `apps/frontend/vite.config.ts:27-30` consumes the whole text
after the final dot. It therefore sees `js;v=1` or `css;anything`, which are absent from
the known-extension set, and the positive headers admit the request at lines 90-102.
The actual-server test covers query-bearing paths but not the planner-requested
semicolon/path-parameter form.

**Violated invariants:** missing resource requests never receive successful SPA HTML;
resource-like paths fail closed; classification uses the correct pathname semantics.

Related observation: explicit document headers also admitted `/file.bin`,
`/file.download`, and `/file.data`. Unknown dotted client paths such as `/foo.xyz` and
`/foo.abc123` are intentionally supportable under the documented dotted-wildcard
contract, so those alone are not treated as defects. The conventional binary/download
suffix results show that the finite extension heuristic remains a weak boundary and
reinforce the exact semicolon bypass above.

### HTTP2-F-02 — HIGH — Malformed `q` parameter is positively admitted

Exact real-server request:

```http
GET /dashboard HTTP/1.1
Host: 127.0.0.1:5173
Accept: text/html;q
Sec-Fetch-Dest: document
```

| Status | Content-Type | SPA shell | Expected classification |
|---:|---|---|---|
| `200` | `text/html` | Yes (`<div id="root"></div>`) | Malformed HTML quality parameter; fail closed |

At `apps/frontend/vite.config.ts:40-42`, a parameter without `=` is skipped. The
default quality therefore remains `1`, and the malformed `q` token becomes positive
HTML admission. This is inconsistent with the remediation's claimed fail-closed
handling for malformed `q` values and with the round-two requirement that malformed
q-values must not accidentally admit HTML.

The requested malformed controls `q=abc`, `q=`, `q=2`, `q=-1`, `q=0.0001`, and
duplicate `q=0;q=1` did fail closed. The newly tested missing-equals form exposes the
remaining parser gap.

**Violated invariant:** malformed/ambiguous requests fail closed rather than becoming
a successful HTML response.

### HTTP2-F-03 — HIGH — Decode-bound output can become malformed and still be admitted

Exact real-server request:

```http
GET /dashboard%252525 HTTP/1.1
Host: 127.0.0.1:5173
Accept: text/html
Sec-Fetch-Dest: document
```

| Status | Content-Type | SPA shell | Expected classification |
|---:|---|---|---|
| `200` | `text/html` | Yes (`<div id="root"></div>`) | Ambiguous/malformed bounded decode; fail closed |

The three decode rounds produce `/dashboard%2525`, `/dashboard%25`, and finally
`/dashboard%`. At the bound, `canonicalPathForms()` checks only for another complete
encoded octet with `/%[0-9a-f]{2}/i` (`apps/frontend/vite.config.ts:60-75`). The
dangling percent is therefore marked unambiguous even though directly supplied
malformed forms such as `/dashboard%ZZ`, `/malformed%`, and `/dashboard%25` fail
closed.

The implementation is not required to decode indefinitely. It is required to reject
ambiguity beyond the bound and malformed derived forms. This boundary-shaped input is
admitted instead.

**Violated invariant:** bounded canonicalization must fail closed for unresolved or
malformed ambiguity.

### HTTP2-F-04 — HIGH — Existing `/index.html` resource is blocked

Exact real-server request:

```http
GET /index.html HTTP/1.1
Host: 127.0.0.1:5173
Accept: text/html
Sec-Fetch-Dest: document
```

| Status | Content-Type | SPA shell | Expected classification |
|---:|---|---|---|
| `404` | `text/plain; charset=utf-8` | No | Existing Vite entry resource; successful HTML response |

`HEAD /index.html` also returned `404`. The file exists at
`apps/frontend/index.html`. The custom boundary runs after public/transform/static
middleware but before Vite's index middleware. Because `html` is in
`RESOURCE_EXTENSIONS`, the boundary denies the request before Vite can serve the real
entry document.

Other existing controls remained healthy: `/@vite/client`, `/src/main.tsx`,
`/src/styles.css`, and `/src/styles.css?v=1` returned `200 text/javascript`; their HEAD
requests returned the same truthful status and type with no body. The defect is not a
blanket resource outage, but it directly violates the mandatory existing-resource
control.

**Violated invariant:** existing resources still work with truthful GET/HEAD behavior.

### HTTP2-F-05 — HIGH — Reserved Vite module paths can fall through as SPA navigation

Exact real-server request:

```http
GET /@id/__x00__virtual:phase15c-missing HTTP/1.1
Host: 127.0.0.1:5173
Accept: text/html
Sec-Fetch-Dest: document
```

| Status | Content-Type | SPA shell | Expected classification |
|---:|---|---|---|
| `200` | `text/html` | Yes (`<div id="root"></div>`) | Missing Vite virtual module; no SPA fallback |

The same document headers converted `/@vite/env` and `/@react-refresh` into SPA HTML.
Under their legitimate resource headers (`Accept: */*`, `Sec-Fetch-Dest: script`), the
latter two correctly returned `200 text/javascript`; the missing virtual module
returned `404`. This proves the middleware itself can distinguish the development
resource behavior, but the custom pathname classifier does not reserve Vite's internal
resource namespaces. One positive document signal overrides an otherwise obvious
non-application resource path.

**Violated invariants:** Vite internal/virtual resource requests must be classified
truthfully and must not escape through custom classification into `index.html`.

## 4. First-Round Finding Replay

All four original bypasses are closed on the actual configured server:

| Request | Headers | Fresh result |
|---|---|---|
| `GET /resource-without-extension` | `Accept: */*`; `Sec-Fetch-Dest: empty` | `404 text/plain; charset=utf-8`; no shell |
| `GET /foo%252Ejs` | `Accept: text/html`; `Sec-Fetch-Dest: document` | `404 text/plain; charset=utf-8`; no shell |
| `GET /trailing-dot.` | `Accept: text/html`; `Sec-Fetch-Dest: document` | `404 text/plain; charset=utf-8`; no shell |
| `GET /foo/file.xyz` | `Accept: text/html;q=0, */*;q=1`; `Sec-Fetch-Dest: document` | `404 text/plain; charset=utf-8`; no shell |

The round-two verdict is therefore not a stale replay of the first report. It is based
on newly demonstrated bypasses and the newly demonstrated existing-resource regression.

## 5. Accept and Fetch-Destination Matrix

### Accept parsing

On `/dashboard` with `Sec-Fetch-Dest: document`, these positive forms returned the SPA
shell as intended:

- `text/html`
- `text/html;q=1`
- `text/html;q=1.0`
- `text/html;q=0.5`
- `TEXT/HTML`
- `Text/Html;Q=0.8`
- `application/json, text/html;q=0.8`
- `text/html;q=0.8, application/json;q=1`
- `text/html ; q = 0.8`
- `text/html;charset=utf-8`
- `text/html;level=1;q=0.7`

These requested zero/malformed forms returned `404` and no shell:

- `text/html;q=.5`
- `text/html;q=0`, `q=0.0`, and `q=0.000`
- `text/html;q=000`
- `text/html;q=abc`
- `text/html;q=`
- `text/html;q=2`
- `text/html;q=-1`
- `text/html;q=0.0001`
- `text/html;q=0;q=1`
- `text/html;q=0, */*;q=1`
- `*/*;q=1, text/html;q=0`

Two separate `text/html` ranges, one at `q=0` and one at `q=0.5`, were admitted,
which is consistent with a positive HTML range being present. `text/html;q` is the
fail-open malformed case recorded as HTTP2-F-02.

For an extensionless unknown path, `*/*`, `application/json`, `text/plain`,
`application/javascript`, `text/css`, `image/*`, `font/woff2`, and
`application/octet-stream` all returned `404`, never SPA HTML. `/dashboard` with
explicit `text/html` and no `Sec-Fetch-Dest` returned the shell, preserving approved
direct/deep-link semantics.

### `Sec-Fetch-Dest`

For `/dashboard` with `Accept: text/html`, `document`, `iframe`, mixed-case `DoCuMeNt`,
whitespace-padded `document`, and an absent header were admitted. `empty`, `script`,
`style`, `image`, `font`, `manifest`, `worker`, `audio`, `video`, `object`, `report`,
`embed`, `track`, and `unknown-token` all returned `404` and no shell.

For `/missing.js`, every tested destination—including `document`, `iframe`, and absent—
returned `404`. The destination logic is otherwise fail-closed and a positive document
signal does not override a recognized resource extension.

## 6. Canonicalization, Dots, and URL-Component Results

### Bounded decoding

All requested encoded resource forms returned `404` and no shell:

- `/foo%2Ejs`, `/foo%252Ejs`, `/foo%25252Ejs`, `/foo%2525252Ejs`;
- `/images/a%2Epng`, `/images/a%252Epng`, `/images/a%25252Epng`;
- `/foo%2eJS`, `/foo%252eJs`;
- `/foo%2Fbar.js`, `/foo%252Fbar.js`, `/foo%5Cbar.js`, and
  `/foo%255Cbar.js`.

Inputs retaining a complete encoded octet beyond the three-round bound also failed
closed. The derived dangling-percent exception is HTTP2-F-03.

### Dot and extension behavior

- Terminal-dot paths `/trailing-dot.` and `/double-dot..` returned `404`.
- Known extensions, including uppercase/mixed-case JavaScript, image, font, and CSS,
  returned `404` when missing.
- `/foo.bar/baz.js` and `/path.with.many.dots/resource.css` returned `404`.
- Explicit HTML document navigation remained available for `/foo..bar`, `/.hidden`,
  `/.well-known/example`, `/foo.bar/`, `/foo.bar/baz`, `/foo.bar/baz.qux`, and
  `/path.with.many.dots/client-route`.
- `/foo.xyz` and `/foo.abc123` also remained eligible dotted wildcard routes under
  explicit HTML/document headers.
- `/missing.js;v=1` and its encoded form expose HTTP2-F-01.

`/.` and `/..` were rejected by the observed curl/Vite path handling and did not return
the shell.

### Query separation

The query string did not alter normal resource classification:

- `/missing.js?route=/dashboard` -> `404`;
- `/missing.css?x=.html` -> `404`;
- `/dashboard?file=missing.js` -> SPA shell;
- `/foo%252Ejs?accept=text/html` -> `404`;
- `/trailing-dot.?x=1` -> `404`.

Semicolon/path-parameter-like content is part of the pathname and is mishandled as
HTTP2-F-01. An encoded question mark inside the pathname also demonstrated the same
class: `/missing.js%3Froute=/dashboard` returned SPA HTML.

## 7. Navigation, Resources, API, Methods, and Middleware Ordering

### Navigation controls

Every required Phase 15C route returned `200 text/html` with the SPA shell under
`Accept: text/html` and `Sec-Fetch-Dest: document`:

- `/`, `/dashboard`, `/new-onboarding`, and retained-intake deep link;
- `/cases` and case detail;
- `/onboarded` and onboarded detail;
- `/audit` and audit detail;
- `/policy`, `/admin/users`, and `/admin/teams`;
- wildcard `/wildcard/client-route`;
- dotted wildcard `/reports/quarter.v2`;
- query-bearing `/dashboard?view=all`.

`HEAD /dashboard` and `HEAD /reports/quarter.v2` returned `200 text/html` with empty
bodies. Valid navigation was not broken generally.

### Existing-resource controls

- `/@vite/client`, `/src/main.tsx`, `/src/styles.css`, and
  `/src/styles.css?v=1`: GET and HEAD `200 text/javascript`, no SPA shell.
- `/index.html`: GET and HEAD `404 text/plain`, HTTP2-F-04.
- `/@react-refresh` and `/@vite/env`: legitimate script requests returned
  `200 text/javascript`; contradictory document headers exposed HTTP2-F-05.

### API boundary

With port 8000 intentionally free, `GET /api/nonexistent`, `GET /api/foo.js`,
`GET /api/foo%252Ejs`, and `HEAD /api/nonexistent` reached the configured proxy and
returned proxy-owned `500 text/plain` after `ECONNREFUSED`; none returned SPA HTML.
The focused real-server test supplied its isolated local backend and freshly passed the
stronger controls: `/api/auth/me` returned `401 application/json`, while missing API
paths returned `404 application/json`.

### Method boundary

`POST`, `PUT`, `PATCH`, and `DELETE /dashboard` returned `404 text/plain`, never the SPA
shell. `OPTIONS /dashboard` returned `204` with no body and no SPA shell. Unsafe methods
remain outside the fallback.

### Middleware ordering conclusion

The custom boundary correctly sits after Vite's proxy/public/transform/static handling
and before final index transformation for ordinary misses. That placement preserves
known transformed modules, but it also means:

- the custom classifier can block Vite's real index resource (HTTP2-F-04); and
- unresolved Vite-reserved/virtual paths not named by the classifier can continue to
  the SPA shell (HTTP2-F-05).

These are concrete middleware-order/classification escapes, not inferred helper-only
concerns.

## 8. Closed Frontend Findings

- **F-01 remains closed.** The focused Phase 15C suite passed the router-integrated
  CaseDetail generation/case/actor action-isolation scenarios. Stale Case A dialog,
  success, failure, and history effects cannot migrate to Case B.
- **F-04 remains closed.** The same suite passed the six deferred create, upload, and
  completion tests across explicit fresh reset and logout/replacement login.
- The complete Windows lifecycle suite was not rerun. The accepted unchanged owner
  evidence remains **18/18 PASS in 266.225 seconds**, and the real-server work revealed
  no startup/root-health regression. Pre/post cleanup independently confirmed both
  required ports free and the runtime manifest absent.

## 9. Verification Results

| Check | Fresh result |
|---|---|
| Focused Vite fallback + Phase 15C navigation | PASS — 26/26 across 2 files |
| Real configured Vite adversarial matrix | **FAIL — HTTP2-F-01 through HTTP2-F-05** |
| Full frontend suite | PASS — 181/181 across 9 files; existing non-failing React Router SSR warnings |
| Frontend typecheck | PASS |
| Frontend production build | PASS — 108 modules; output written to and removed from a verified temporary directory; JS 345.33 kB / gzip 100.62 kB; CSS 59.25 kB / gzip 12.65 kB |
| `python scripts/check_architecture.py` | PASS |
| `python scripts/check_project_state.py` | PASS |
| `python scripts/check_secrets.py` | PASS |
| `git diff --check` before report | PASS; line-ending warnings only |
| F-01/F-04 focused regression | PASS within the 25-test Phase 15C suite |
| Phase 15C Windows lifecycle | NOT RERUN — accepted unchanged evidence remains 18/18 PASS, 266.225 seconds |
| Physical Mongo | NOT APPLICABLE |

The first in-sandbox focused Vitest attempt failed before collection with esbuild
`spawn EPERM`. The identical command was rerun with the required process permission and
passed 26/26. The server start followed the same pattern. These are environment
restrictions, not code-test failures.

## 10. Production Hosting Boundary

Production-host fallback remains explicitly **UNVERIFIED / OUT OF SCOPE**:

- the planner excludes deployment-platform configuration not present here;
- the execution addendum separates local Vite evidence from production-host evidence;
- ADR-001 assigns production fallback to the later deployment owner; and
- `docs/ARCHITECTURE.md` says local Vite behavior is development evidence only.

The implementation and reports continue to state this boundary truthfully. No
production-host equivalence claim is made, and the absence of production-host evidence
is not classified as a defect in this verdict.

## 11. Consequence and Next Action

Phase 15C cannot receive PASS. The required next action is a new bounded remediation of
the existing Vite development HTTP boundary, followed by another independent
real-server falsification. That work must close the exact reproducible failures above
while preserving the now-green first-round cases, valid document navigation, existing
resources, API ownership, unsafe-method exclusion, HEAD truthfulness, F-01, and F-04.

This FAIL authorizes no remediation, stage, commit, push, PR, merge, rebase, reset,
stash, clean, latest-main integration, deployment, or next phase.
