# Phase 15C — Vite HTTP Fallback Architecture Remediation

## Decision

**ARCHITECTURE REMEDIATION: PROCEED**

Replace the current `appType: "spa"` classifier-in-front-of-index design with:

```text
Vite 7.1.11 with appType: "mpa"
  -> proxy/public/transform/raw-fs/static middleware
  -> Vite MPA HTML fallback (existing HTML files only; no SPA catch-all)
  -> returned configureServer middleware
       -> positively admitted unresolved navigation: rewrite to /index.html
       -> every other unresolved request: next()
  -> Vite indexHtmlMiddleware
       -> read index.html
       -> server.transformIndexHtml(...)
       -> truthful GET/HEAD HTML response
  -> Vite notFoundMiddleware
       -> truthful 404
```

This is a refinement inside the existing Vite development-server owner. It does not
add another business router, copy the React Router route table, move fallback into the
backend, or take ownership of Vite module/static/HTML transformation.

`appType: "custom"` is rejected for this remediation because Vite 7.1.11 omits both
its HTML-serving middleware and final HTML/not-found sequence in custom mode. The
repository would then need to read `index.html`, call `transformIndexHtml`, reproduce
headers/HEAD/error behavior, and own more of Vite's HTML contract. `mpa` disables only
the automatic SPA catch-all while retaining Vite's HTML owner.

## 1. Scope, role, and change classification

This file is a read-only planner result. No implementation or test file is modified by
this planning run.

The future remediation is classified as:

- `ARCHITECTURE_REFACTOR`: replace the current pre-index resource-classifier boundary
  with Vite-first ownership plus a narrow unresolved-navigation rewrite;
- `CI_TOOLING`: change Vite development-server configuration and its actual-server
  HTTP contract test;
- `FRONTEND_UI`: direct-entry/refresh behavior is a browser-facing compatibility
  surface, although no React view or route-table change is expected.

No backend API, shared model/type, React Query/cache, authentication/RBAC,
persistence, external provider, business rule, mapping, lifecycle, production host,
or Phase 15B change is authorized.

The supplied worktree and branch are:

- worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-15c`;
- branch: `phase/15c-frontend-navigation`.

No Git command, latest-main integration, sibling-worktree inspection, implementation,
test execution, commit, push, PR, merge, or deployment is part of this planner run.

## 2. Authority and evidence read

Repository authority was read in the required order, followed by the Phase 15C
planner, execution addendum, implementation report, original quality gate, re-quality
gate, both HTTP falsification reports, current Vite configuration, actual-server test,
and frontend package metadata.

Relevant current repository decisions are:

- browser location and `navigation.tsx` remain the sole client page/case navigation
  owner;
- Vite remains the local development HTML/static/module owner;
- the backend remains the API/RBAC owner;
- SPA fallback must not absorb API, static/file, or unsafe-method requests;
- local Vite evidence is not production-host evidence.

The actual installed Vite version is exactly **7.1.11**:

- `apps/frontend/package.json` pins `vite: "7.1.11"`;
- `apps/frontend/package-lock.json` records `node_modules/vite` version `7.1.11`;
- the installed package at `apps/frontend/node_modules/vite` is 7.1.11;
- no version upgrade is required or authorized.

### Official documentation and exact-version source evidence

Current official Vite documentation:

- `appType`: <https://vite.dev/config/shared-options.html#apptype>
  - `spa` includes HTML middleware and SPA fallback;
  - `mpa` includes HTML middleware without the SPA fallback;
  - `custom` excludes HTML middleware.
- `configureServer`: <https://vite.dev/guide/api-plugin.html#configureserver>
  - ordinary middleware registration is before Vite internals;
  - a function returned from `configureServer` registers post middleware.
- `transformIndexHtml`: <https://vite.dev/guide/api-plugin.html#transformindexhtml>
  - HTML entry files pass through Vite's HTML transformation hooks.

Exact tagged Vite 7.1.11 source:

- server assembly:
  <https://github.com/vitejs/vite/blob/v7.1.11/packages/vite/src/node/server/index.ts>;
- history behavior:
  <https://github.com/vitejs/vite/blob/v7.1.11/packages/vite/src/node/server/middlewares/htmlFallback.ts>;
- index handling:
  <https://github.com/vitejs/vite/blob/v7.1.11/packages/vite/src/node/server/middlewares/indexHtml.ts>;
- app-type definition/default:
  <https://github.com/vitejs/vite/blob/v7.1.11/packages/vite/src/node/config.ts>.

The checked-in installed bundle independently confirms the tagged source at
`apps/frontend/node_modules/vite/dist/node/chunks/config.js`:

1. proxy runs before public/static/module handling;
2. public files run before transforms;
3. transform middleware runs before raw filesystem and root static middleware;
4. `spa` and `mpa` both install `htmlFallbackMiddleware`, but only `spa` passes
   `spaFallback=true`;
5. returned `configureServer` hooks run after that history middleware;
6. returned hooks run before `indexHtmlMiddleware` and `notFoundMiddleware`;
7. `indexHtmlMiddleware` reads an existing `.html` file and, in development, calls
   `server.transformIndexHtml(url, html, req.originalUrl)`;
8. `custom` skips the history, index-HTML, and not-found block entirely.

The official plugin documentation's phrase “after internal middlewares” is therefore
not sufficiently precise for this version-specific design. In Vite 7.1.11, a returned
hook is specifically **after proxy/public/transform/static and MPA history handling,
but before Vite's index-HTML and final 404 middleware**. The implementation and tests
must rely on that exact verified order, not on an assumed latest-version layout.

## 3. Root cause and change necessity

The current `appType: "spa"` flow lets Vite rewrite an unresolved request to
`/index.html` before the returned custom boundary. The custom middleware must retain
the original URL, infer whether it was a resource or navigation, and either allow or
block Vite's already-selected index response.

That position creates the repeated failure pattern:

- every new resource shape becomes another classifier exception;
- the guard can block genuine Vite HTML such as `/index.html`;
- Vite internal/virtual namespaces have to be rediscovered outside their owner;
- Accept normalization mutates a request solely to accommodate Vite's SPA substring
  precondition;
- the custom layer is forced to distinguish application navigation from all possible
  Vite resources before Vite has completed HTML handling.

A further extension-only patch is insufficient. The minimum stable correction is to
disable Vite's automatic SPA catch-all while retaining Vite's resource and HTML
middleware, then add only a positive unresolved-navigation rewrite.

## 4. Architecture review

**ARCHITECTURE REVIEW: PROCEED**

### Existence check

Existing candidates:

- React Router: owns client route matching after HTML loads, but cannot decide whether
  the server should return HTML for an HTTP request;
- backend: owns `/api/**` and RBAC, and must not become a development SPA host;
- current Vite plugin: already owns the local development fallback boundary;
- Vite 7.1.11 `mpa` middleware preset: already supplies the required resource, HTML,
  transformation, and 404 owners without automatic SPA catch-all.

Conclusion: reuse the existing Vite plugin and Vite's `mpa` preset. Do not create a
new service, router, server, dependency, or route table.

### Before/after ownership

| Responsibility | Current owner/problem | Remediated owner |
|---|---|---|
| Client route matching | React Router | unchanged |
| API proxy/backend response | Vite proxy then backend | unchanged and runs first |
| HMR, virtual modules, source transforms | Vite transform middleware/plugins | unchanged and runs first |
| Public/root/static files | Vite public/raw-fs/static middleware | unchanged and runs first |
| Existing HTML including `/index.html` | reachable only through a classifier that can shadow it | Vite MPA fallback plus `indexHtmlMiddleware` |
| SPA history admission | Vite SPA fallback plus custom negative classifier | one custom positive admission rewrite |
| HTML transforms/HMR injection | Vite `indexHtmlMiddleware` | unchanged; custom code delegates to it |
| Unresolved 404 | custom response in front of Vite index | Vite `notFoundMiddleware` |

### Dependency direction

```text
HTTP request
  -> Vite proxy/public/transform/static owners
  -> narrow positive navigation admission
  -> Vite index HTML transform or Vite 404
  -> React Router after the document loads
```

There is no frontend-to-backend-storage direction, no backend fallback, no React route
table import into `vite.config.ts`, and no route-driven business mutation.

### Entropy and retirement

Retire in the same change:

- `appType: "spa"` behavior for the local dev server;
- the pre-Vite URL-capture/Accept-normalization middleware;
- the design in which Vite rewrites every candidate before custom admission;
- custom terminal 404 response ownership.

Retain, but narrow:

- deterministic navigation-admission helpers;
- the bounded canonicalization and strict Accept contracts;
- resource/reserved-namespace checks needed only for an unresolved request.

No compatibility flag or second fallback path is permitted. The old and new fallback
architectures must not coexist.

### ADR decision

No new ADR is required. ADR-001 already assigns client navigation to React Router and
requires a safe development/deployment history fallback. This remediation keeps the
same canonical owners and changes how the existing Vite owner satisfies that
requirement. ADR-001 remains Proposed until independent Phase 15C acceptance; this
planner does not change its status.

## 5. Exact Vite configuration decision

Set:

```ts
appType: "mpa"
```

Do not use `appType: "custom"`.

The plugin continues to use a function returned from `configureServer`, but its role
changes from “block Vite's SPA rewrite before index serving” to “admit one unresolved
request to Vite's index owner.”

Conceptual implementation:

```ts
configureServer(server) {
  return () => {
    server.middlewares.use((request, _response, next) => {
      // Vite proxy/public/transform/raw-fs/static and MPA HTML-file resolution
      // have already run.
      if (requestTargetsExistingOrRewrittenHtml(request)) {
        next(); // Vite indexHtmlMiddleware owns it, including /index.html.
        return;
      }

      if (isAdmittedSpaNavigation(originalRawPath(request), request)) {
        request.url = "/index.html";
      }

      // Positive navigation reaches Vite indexHtmlMiddleware.
      // Rejected/unresolved traffic reaches Vite notFoundMiddleware.
      next();
    });
  };
}
```

The production implementation may express the existing/re-written HTML pass-through
differently, but it must preserve these semantics:

- `/index.html` is never handled or rejected by the navigation classifier;
- an existing `.html` file/directory rewrite produced by Vite MPA handling continues
  to Vite's index middleware;
- the custom middleware does not read `index.html`, call filesystem APIs, manually set
  HTML headers, or write the response body;
- only a positively admitted unresolved navigation mutates `request.url` to
  `/index.html`;
- `request.originalUrl` remains available to Vite's HTML transform context;
- every rejected request calls `next()` and receives Vite's final truthful 404.

This indirect use of `server.transformIndexHtml` is preferred to calling it manually:
Vite's own `indexHtmlMiddleware` performs the file read, transform hook chain, HMR
injection, headers, errors, and HEAD behavior.

## 6. Requests that remain Vite-owned

Vite must get first opportunity to consume:

- `/` and every existing HTML file, especially `/index.html`;
- configured `/api/**` proxy traffic;
- existing `public/**` and root static files;
- `/@vite/client` and `/@vite/env`;
- `/@fs/**` filesystem module traffic;
- `/@id/**` encoded/virtual module traffic;
- `/@react-refresh` from `@vitejs/plugin-react`;
- `/src/**` source modules and styles;
- transformed CSS/JS/module requests, HMR queries, and genuine virtual modules;
- other requests consumed by the installed Vite/plugin transform chain.

The fallback middleware runs only after those handlers have declined the request.
Passing an existing `.html` request onward is also delegation to Vite, not custom HTML
ownership.

## 7. Positive navigation-admission contract

An unresolved request may be rewritten to `/index.html` only if **all** conditions are
true:

1. method is exactly `GET` or `HEAD`;
2. the raw path can be extracted without URL ambiguity;
3. bounded canonicalization succeeds and leaves no malformed or unresolved percent
   encoding;
4. no raw or decoded form is `/api` or under `/api/`;
5. no raw or decoded form is in a reserved Vite/project-resource namespace;
6. no raw or decoded form is resource-like;
7. no raw or decoded path contains unsupported semicolon/matrix parameters;
8. `Accept` contains a syntactically valid `text/html` range with effective `q > 0`;
9. `Sec-Fetch-Dest` is absent or is exactly a supported navigation destination;
10. Vite's earlier middleware has not already ended the response.

Failure of any condition means no rewrite. The request continues to Vite's 404 owner.

Do not compare the request against the React Router route table. The wildcard client
route is intentional, and duplicating the route table would create a second route
authority. Positive HTTP navigation evidence, not server-side knowledge of individual
application paths, is the admission boundary.

## 8. Accept parser contract

The helper must parse comma-separated media ranges case-insensitively and apply this
contract specifically to every `text/html` range:

- no `q` parameter means quality `1`;
- one `q` parameter is allowed;
- `q` must match the HTTP q-value shape for a value in `[0,1]`, with no more than three
  fractional digits and no non-zero fractional digit after `1`;
- `q=0`, `q=0.0`, and `q=0.000` reject that HTML range;
- malformed `q`, including `q`, missing `=`, empty value, `.5`, `000`, negative,
  greater than one, more than three fractional digits, or duplicate `q`, rejects SPA
  admission for the entire request;
- malformed parameter syntax on a `text/html` range fails closed rather than being
  ignored;
- parameters and media types are case-insensitive, with optional HTTP whitespace;
- a request is admitted only if all HTML ranges are syntactically valid and at least
  one valid HTML range has `q > 0`;
- `*/*` alone, missing/empty Accept, and non-HTML ranges do not positively admit SPA
  HTML;
- a positive non-HTML range never overrides `text/html;q=0`.

The parser should use a small bounded scanner/helper that does not split inside quoted
parameter values, or conservatively reject quoted/escaped syntax it does not support.
It must not use substring matching. No request-header normalization for Vite's SPA
fallback remains necessary after selecting `mpa`.

Required navigation-positive controls include `text/html`, mixed-case media/parameter
names, valid positive q-values, and mixed lists with a positive HTML range. Required
negative controls include every malformed/zero form observed in both falsification
reports, especially `Accept: text/html;q`.

## 9. Canonicalization contract

Canonicalization is bounded to **three decode rounds** and fails closed.

For the raw pathname (literal query string removed before classification):

1. require an absolute path beginning with `/`;
2. retain the raw form as the first classified form;
3. before each decode, reject any `%` not followed by exactly two hexadecimal digits;
4. decode with `decodeURIComponent`; any exception rejects admission;
5. retain every decoded form for API/resource/reserved/matrix classification;
6. stop early only when the value is stable or contains no `%`;
7. after the third round, reject if **any** percent sign remains, whether it starts a
   valid octet or is malformed;
8. reject a decoded form that introduces a path/query/fragment ambiguity, control/NUL,
   or backslash; encoded path separators are not required by any Phase 15C route;
9. reject dot-segment ambiguity (`.` or `..` path segments) rather than normalize it
   into a different application route;
10. classify every retained form; a negative classification in any form wins.

Do not recursively decode without a bound. Do not treat the absence of a complete
`%HH` triplet after the final round as success: a dangling `%` is malformed.

This contract rejects `/dashboard%252525` because the bounded result contains a
dangling percent, while also rejecting malformed input at any intermediate stage and
encoded resource forms revealed within the bound.

## 10. Semicolon and resource contract

Matrix/path parameters are not an authorized Phase 15C navigation feature. If any raw
or decoded path segment contains `;`, SPA admission fails closed.

For diagnostic classification, the segment stem before the first semicolon must still
be inspected. A recognized resource suffix in that stem is resource-like. Therefore:

- `/missing.js;v=1` is a resource miss, never a document route;
- `/missing.js%3Bv=1` becomes the same rejected shape;
- `/missing.css;anything` is rejected;
- a semicolon on an otherwise extensionless path is also rejected as unsupported
  matrix ambiguity rather than silently admitted.

Resource-like detection is evaluated over all canonical forms and includes:

- `/assets` and `/assets/**`;
- a final segment ending in `.`;
- the existing bounded, case-insensitive established web-resource extension set,
  including `.html`;
- resource stems before a semicolon (in addition to the general semicolon rejection);
- requests whose present `Sec-Fetch-Dest` is not navigation-compatible;
- requests without positive HTML Accept permission.

An arbitrary unknown suffix cannot be classified from its name alone without breaking
the intentional dotted wildcard route. The deterministic distinction is:

- explicit valid HTML + navigation destination + otherwise safe dotted path may be a
  wildcard client navigation and is admitted;
- unknown extension with resource/non-HTML Accept or non-navigation destination is a
  resource miss and receives 404.

No ever-growing list of React application routes is introduced.

## 11. Reserved namespace contract

Vite and installed plugins run first. If they do not consume a request in one of their
reserved/project-module namespaces, the SPA fallback must still reject it.

For the installed Vite 7.1.11 and React plugin baseline, reserve at minimum:

- `/@vite/` (including `/@vite/client` and `/@vite/env`);
- `/@fs/`;
- `/@id/`;
- `/@react-refresh` and any child path;
- `/src/`;
- `/node_modules/`;
- `/assets` and `/assets/`;
- Vite's explicit editor/internal endpoints used by the installed server, such as
  `/__open-in-editor` and a bounded `/__vite` internal prefix.

Apply the check to every canonical form. Exact values must be derived from Vite 7.1.11
constants and `@vitejs/plugin-react` paths already installed in this repository; do
not invent a broad `"/@"` business rule or import private Vite implementation modules.

Expected behavior:

- a genuine `/@vite/client`, `/@vite/env`, `/@react-refresh`, `/src/main.tsx`, or other
  existing module is consumed before the fallback;
- an unresolved `/@id/**`, `/@vite/**`, `/@fs/**`, `/src/**`, or React-refresh path is
  passed through to Vite's 404 and never rewritten to application HTML, even with
  adversarial document headers.

## 12. Resolution of the five current defects

| Defect | Architectural resolution |
|---|---|
| `/missing.js;v=1` returns SPA HTML | Vite gets first chance; unresolved request reaches positive admission; any semicolon fails closed and the pre-semicolon `.js` stem is resource-like; Vite not-found returns 404. |
| `Accept: text/html;q` is admitted | strict HTML-range parsing treats missing `=`/value as malformed and rejects the whole SPA admission. |
| `/dashboard%252525` is admitted | three bounded decode rounds end with malformed `%`; final residual-percent validation rejects admission. |
| `/index.html` returns 404 | `mpa` retains Vite HTML middleware; `.html` requests pass through untouched to `indexHtmlMiddleware`, which reads and transforms the existing file. |
| Vite internal/virtual paths fall through | Vite transform/static handlers run before the custom hook; unresolved reserved namespaces are never navigation-admitted and reach Vite's 404. |

## 13. Expected implementation files

### Modify

| File | Bounded change |
|---|---|
| `apps/frontend/vite.config.ts` | Set `appType: "mpa"`; replace pre-normalization/post-block classifier with the narrow post-core/pre-index navigation rewrite; implement strict Accept, bounded canonicalization, semicolon, resource, and reserved-namespace contracts; remove custom 404 response ownership. |
| `apps/frontend/ViteHistoryFallback.test.ts` | Expand the actual Vite server matrix for Vite-owned HTML/modules/static, resource misses, malformed input, navigation, API, HEAD, unsafe methods, semicolon variants, decode-bound residue, and reserved namespace misses. |
| `.ai-pipeline/reports/PHASE_15C_IMPLEMENTATION.md` | Append remediation evidence only after execution; preserve all prior gate/falsification history and distinguish local Vite from production hosting. |

### No implementation change expected

- React components, `navigation.tsx`, route table, auth/query/cache/API modules;
- backend, contracts, persistence, providers, lifecycle/CI scripts;
- package manifest or lockfile;
- `docs/ARCHITECTURE.md` and ADR-001, whose existing owner/invariant statements remain
  correct;
- previous independent quality-gate and falsification reports.

If implementation requires any additional production file, the implementer must stop
and return to planning with the exact reason rather than silently broaden scope.

## 14. Implementation sequence

### Task 1 — Replace fallback architecture inside the existing Vite owner

1. Record a task-start snapshot without integrating main or touching sibling
   worktrees.
2. Add `appType: "mpa"`.
3. Remove the pre-Vite Accept-lowercasing/original-URL workaround.
4. Keep one returned `configureServer` middleware.
5. Pass existing/MPA-rewritten `.html` requests through to Vite.
6. Rewrite only positively admitted unresolved navigation to `/index.html`.
7. Pass all rejected requests onward to Vite's not-found middleware.
8. Do not read/serve HTML or emit a custom 404 in the plugin.

### Task 2 — Harden admission helpers without creating a route authority

1. Implement the strict Accept contract.
2. Implement bounded canonical forms with final residual/malformed checks.
3. Fail closed on matrix/semicolon syntax in any form.
4. Retain the bounded known-resource rules needed for missing resources.
5. Add the exact installed Vite/React reserved namespaces.
6. Keep React routes out of the server helper.

### Task 3 — Expand actual-server falsification coverage

1. Exercise the repository config through `createServer`, not helper-only unit tests.
2. Add all cases in section 15.
3. Assert status, content type, body identity, and HEAD body emptiness where relevant.
4. Prove existing transformed resources are still real Vite responses.
5. Prove rejected requests never contain the SPA marker.

### Task 4 — Run proportional verification and report evidence

1. Run the focused real-server and Phase 15C navigation suites.
2. Run the full frontend suite, typecheck, and build.
3. Run architecture, project-state, secret, and diff checks.
4. Append the implementation report with exact version, commands, counts, and residual
   production-host boundary.
5. Hand the result to a new independent adversarial falsification/re-quality gate.

This planner does not authorize Task execution.

## 15. Required actual-server test matrix

Every row is tested against the actual configured Vite server with an isolated fixture
root and bounded local backend where API response truth is asserted.

### Vite-owned success

| Request | Required result |
|---|---|
| `GET /` and `HEAD /` | `200 text/html`; transformed fixture index; empty HEAD body |
| `GET /index.html` and `HEAD /index.html` | `200 text/html`; transformed fixture index; empty HEAD body |
| known public/root JS and CSS | truthful `200`, Vite content type, exact non-HTML body |
| `/@vite/client` | `200` transformed JavaScript, not SPA HTML |
| `/@vite/env` where served | `200` transformed JavaScript, not SPA HTML |
| `/@react-refresh` | `200` transformed JavaScript, not SPA HTML |
| representative `/src/main.tsx` and style module | `200` transformed module response, not SPA HTML |

If an “existing” internal control is not present in the isolated fixture/plugin
composition, replace it with an actually installed equivalent and record why; do not
turn an expected existing control into a 404 assertion silently.

### Resource misses

Assert `404`, non-HTML, and no SPA marker for GET and representative HEAD:

- `/missing.js`, CSS, module, image, font, map, manifest, document, data, and WASM
  forms already covered;
- `/missing.js;v=1`, `/missing.css;anything`, and encoded-semicolon forms;
- encoded, double-encoded, and triple-encoded resource suffixes;
- terminal dot and double terminal dot;
- uppercase/mixed-case suffixes and query-bearing variants;
- unknown extension with `Accept: application/octet-stream` or another non-HTML
  resource Accept;
- extensionless non-navigation destinations.

### Malformed and ambiguous

Assert `404`, non-HTML, and no SPA marker for:

- `Accept: text/html;q`;
- empty, invalid, negative, out-of-range, over-precision, duplicate, and zero q-values;
- malformed raw percent forms;
- `/dashboard%252525` and other residual-percent-at-bound forms;
- encoded slash/backslash/query/fragment ambiguity;
- matrix/semicolon syntax on otherwise extensionless paths;
- unresolved dot segments if the HTTP client preserves them.

### Navigation

Assert `200 text/html` with the transformed SPA marker for GET and representative HEAD:

- every normal Phase 15C route;
- query-bearing navigation;
- wildcard client route;
- intentional dotted wildcard routes such as `/reports/quarter.v2` and dotted parent
  segments;
- valid mixed-case `text/html` and positive q-values;
- absent `Sec-Fetch-Dest` with explicit valid HTML Accept;
- `document`, `frame`, and `iframe` destinations.

### Reserved namespaces

Assert existing Vite-owned paths succeed as above. Assert unresolved reserved paths
return `404`, never SPA HTML, even with `Accept: text/html` and
`Sec-Fetch-Dest: document`:

- missing `/@id/**` virtual ID;
- missing `/@vite/**`;
- missing `/@fs/**`;
- missing `/@react-refresh/**`;
- missing `/src/**`;
- missing `/assets/**`.

### API, HEAD, and methods

- bounded backend `/api/auth/me` and `/api/missing.js` retain JSON `401`/`404` under
  adversarial HTML headers;
- API encoded forms never receive SPA HTML;
- HEAD matches GET classification and has an empty response body;
- `POST`, `PUT`, `PATCH`, and `DELETE` navigation/resource paths return truthful
  non-SPA responses;
- `OPTIONS` remains Vite/server-owned and is not rewritten.

## 16. Verification commands

Focused evidence first:

```powershell
npm.cmd --prefix apps/frontend test -- --run ViteHistoryFallback.test.ts src/Phase15CNavigation.test.tsx
npm.cmd --prefix apps/frontend run typecheck
npm.cmd --prefix apps/frontend run build
```

Then affected broad evidence:

```powershell
npm.cmd --prefix apps/frontend test -- --run
python scripts/check_architecture.py
python scripts/check_project_state.py
python scripts/check_secrets.py
git diff --check
```

The Git diff command is listed for a later authorized implementation/verification run;
it was not executed by this no-Git planner run.

Backend/contracts and the Windows lifecycle need not be rerun solely for this bounded
Vite-owner change if source identity proves those owners are untouched and the
independent gate accepts the existing evidence. They become required if implementation
touches their files, composition, startup/root health, API proxy contract, or if the
actual-server result indicates a cross-owner regression. Physical Mongo remains not
applicable.

Required final review:

1. an independent real-server adversarial falsification that includes every defect
   from both prior rounds;
2. independent Phase 15C re-quality gate;
3. no ADR acceptance, commit-readiness, or integration claim before that gate passes.

## 17. Acceptance criteria

The remediation is ready for independent review only when all are true:

1. `appType` is exactly `"mpa"` on Vite 7.1.11.
2. No Vite dependency upgrade or package-lock change occurred.
3. Vite proxy/public/transform/raw-fs/static handlers run before fallback admission.
4. Vite's index middleware still owns `/index.html`, HTML transforms, HMR injection,
   headers, errors, and HEAD behavior.
5. Only a positively admitted unresolved GET/HEAD request is rewritten to
   `/index.html`.
6. Rejected requests reach Vite's truthful 404; the plugin emits no custom 404 body.
7. All five round-two defects are closed on the actual server.
8. All four round-one bypasses remain closed.
9. Normal, wildcard, query-bearing, and intentional dotted navigation remain green.
10. Existing static/source/internal/virtual module requests remain Vite-owned and
    functional.
11. Unresolved reserved namespaces never become SPA HTML.
12. API proxy, HEAD, OPTIONS, and unsafe-method boundaries remain truthful.
13. No React Router route table or business rule is duplicated in Vite.
14. No backend, auth, query/cache, persistence, provider, lifecycle, Phase 15B, or
    production-host file changed.
15. Focused/full required checks pass with fresh evidence.
16. Local Vite evidence remains explicitly distinct from production-host verification.
17. A new independent gate, not the implementer, issues the sole acceptance verdict.

## 18. Stop conditions

Stop implementation and return to planning if:

- the installed Vite version is no longer exactly 7.1.11 or its actual middleware
  order differs from the verified source;
- `mpa` does not preserve Vite index transformation, `/index.html`, or existing module
  handling in the actual server;
- the solution requires `appType: "custom"`, direct imports from Vite private
  middleware modules, manual HTML file serving, or a second HTTP server;
- a React Router route table or business-route allowlist becomes necessary;
- the fallback must move into the backend or a production hosting surface;
- any existing Vite-owned resource/internal path is shadowed by the custom middleware;
- malformed Accept, residual encoding, semicolon syntax, API, resource, or reserved
  namespace traffic can still receive the SPA marker;
- valid wildcard/dotted navigation can be preserved only by weakening a demonstrated
  fail-closed boundary without an explicit owner decision;
- implementation requires an unplanned file or dependency change;
- any required focused or broad evidence fails, is skipped, or is narrower than the
  claim;
- latest-main or Phase 15B intent creates an unreconciled owner conflict.

## 19. Planning checks and handoff boundary

**Requirement Ready Check:** ready. The two falsification reports provide concrete
reproduction cases, the target owner split is explicit, and no sponsor/business
authority is required for this local development-server correction.

**Change Necessity:** code-change. Further documentation or another negative extension
rule cannot remove Vite's automatic SPA rewrite; changing `appType` and narrowing the
existing plugin is the minimum architecture correction.

**Architecture Integrity Lens:** proceed. The higher-level fix is to select Vite's
non-SPA HTML middleware preset, not to expand a classifier in front of Vite's index
owner. Vite, React Router, and backend ownership remain singular.

**Complexity pressure:** the current `vite.config.ts` combines parsing,
canonicalization, classification, middleware ordering, and config. Keep helpers local
for this bounded remediation unless the final implementation would make the file
materially less reviewable. If extraction becomes necessary, stop because that would
add an unplanned file; do not create a generic routing utility.

**Compatibility boundary:** preserve every green control from the implementation,
re-QG, and first falsification while closing the five second-round defects. Production
hosting remains unverified and out of scope.

**Retirement boundary:** remove the old `spa`/pre-normalization/custom-404 path in the
same change. No dual fallback or compatibility flag remains.

**Execution route:** a later explicitly authorized remediation should be performed
inline because the config and actual-server test are tightly coupled. This planner run
stops after creating this file.
