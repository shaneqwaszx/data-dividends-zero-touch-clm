# Review/Rework UI Authentication Ordering Diagnosis

Date: 2026-09-20<br>
Role: escalated causal diagnosis and conditionally authorized remediation writer<br>
Status: diagnosis in progress; publication and independent re-quality gate not performed

## Task boundary and preflight

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-review-rework-ui`
- Branch: `followup/review-rework-ui`
- `BASE_SHA`, current `HEAD`, local `origin/main`, and merge base:
  `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Staged paths: none. Active merge, rebase, cherry-pick, revert, and bisect operations:
  none.
- The accepted uncommitted review/rework UI implementation and reports were preserved.
  The current hashes of every final reviewed implementation path match section 18 of
  `REVIEW_REWORK_UI_QUALITY_GATE.md`.
- Available local capabilities: PowerShell and repository read/write access, Git
  read-only inspection, Python 3.12.10, Node 22.23.2, npm 10.9.8, Vitest 3.2.4,
  jsdom 30.0.1, Playwright 1.56.1, installed frontend dependencies, and the existing
  guarded browser/lifecycle harness. No external connector, provider, database,
  credential, protected sponsor artefact, or network service is required or used.
- The coordinator reserves the final guarded browser acceptance sequence. This
  diagnostic writer will not run it. Ports 8867 and 4275 are not reserved by this
  diagnosis.
- Authorized diagnostic write paths are
  `apps/frontend/src/AuthSessionOrdering.test.tsx` and this report. Production writes
  remain conditional and are limited to `apps/frontend/src/auth.tsx` and/or
  `apps/frontend/src/api.ts` after a causal failing test.

## Classification and method

Potential production remediation is classified `FRONTEND_STATE_CACHE` and
`AUTH_RBAC_SECURITY`. The existing `AuthProvider` remains the session lifecycle owner,
the existing authenticated transport remains the CSRF/401 owner, the backend remains
the authorization owner, and the single session QueryClient remains the cache owner.
No API protocol, backend, cookie policy, Vite/lifecycle, persistence, dependency,
provider, or architecture-owner change is authorized.

### Change Necessity

- User-visible need: a request issued for an earlier anonymous or authenticated session
  must not clear or restore a later accepted session, including a later session for the
  same user; a current-session 401 must remain fail-closed.
- No-change / non-code option: selector, timeout, retry, wait, or documentation changes
  cannot correct a transport callback that publishes against the wrong session
  generation. No production change will be made unless the real owner integration test
  first proves that mechanism.
- Why code change is necessary: conditional on RED evidence, the defect is inside the
  existing provider/transport transition owners and can recur independently of E2E
  synchronization.
- Minimum change boundary: capture and validate bounded transport/session generation in
  `api.ts` and `auth.tsx`, with focused actual-provider/actual-transport regressions.
- Decision: `code-change` only if the causal RED test reproduces; otherwise `no-change`
  and return the observed boundary evidence.

### TDD Route

- Mode: `auto`
- Decision: `strict`
- Strict authority: explicit user request for strict test-first diagnosis/remediation
- Test posture: mount the real `AuthProvider` (under `StrictMode` where relevant), use
  the real `api.ts` transport, and control only the completion ordering of
  `globalThis.fetch` deferred responses.
- RED requirement: an obsolete restoration or old-session response must visibly
  invalidate or resurrect the wrong session on the unmodified production owners.
- GREEN requirement: the same deterministic suite must preserve the later session,
  prevent post-logout resurrection, keep current-session 401 invalidation, preserve
  CSRF behavior, and retain normal and denied login behavior.
- Remaining verification: full frontend tests, typecheck/build, backend/security/
  contract/governance/lifecycle checks required by the two change classes, followed by
  the coordinator's separately scheduled browser sequence and independent re-QG.

### Patch shape, owner fit, and complexity

- Patch shape: owner-level stale-transition guard, not a timeout, retry, callback-
  identity comparison, actor-ID comparison, cancellation-only workaround, or ignored
  401.
- Canonical owners: `auth.tsx` for session transitions and `api.ts` for request-bound
  CSRF/unauthorized publication.
- Upward drill: browser symptom -> `AuthProvider` session lifecycle -> authenticated
  transport completion callback. Backend/cookie/Vite/lifecycle changes are a stop
  boundary unless later evidence requires them.
- Owner fit: local fix without new responsibility in the two existing owners. No new
  provider, session store, QueryClient, API protocol, fallback, or compatibility path.
- Complexity budget: two small shared auth owners plus one focused integration suite;
  no extraction or new owner is planned.

## Deterministic experiment design

The focused suite will cover:

1. StrictMode restoration ordering: current anonymous restoration, successful login,
   then obsolete restoration 401;
2. an old-session 401 after a different user's new session;
3. an old-session 401 after a new session for the same user;
4. obsolete successful StrictMode restoration after a later successful login and after
   logout;
5. a genuine current-session 401 clearing the current session and CSRF/query state;
6. normal restoration/login plus an actual denied login.

Only request route labels, status codes, ordinals, state labels, and response order are
used. Tests do not retain passwords, cookies, CSRF values, headers, bodies, complete
URLs, DOM snapshots, traces, screenshots, video, HAR, or storage state.

## Causal RED evidence and pre-claim gate

Focused command:

```text
cd apps/frontend
npm.cmd test -- src/AuthSessionOrdering.test.tsx --run
```

The sandboxed first attempt did not collect because Vite/esbuild child-process spawn was
denied with `EPERM`. The identical permitted command initially collected six tests.
After test-harness rejection handling was made immediate, the clean RED result was three
failures and three passes in 1.12 seconds:

- A failed after the obsolete StrictMode restoration 401: expected
  `authenticated`, received `anonymous` after Maya's successful login;
- B failed after an old-session 401: expected `authenticated`, received `anonymous`
  after Sophia's later session was accepted;
- C failed for the same-user variant: expected `authenticated`, received `anonymous`
  after Maya's later session was accepted;
- D passed: the Effect's existing `current` flag already prevents an obsolete
  successful StrictMode restoration from resurrecting a logged-out session. A distinct
  D1 regression was then added to prove that such a success also cannot replace a later
  accepted login, while D2 retains the logout case;
- E passed: a genuine current-session 401 clears the session, and a later unsafe
  request carries no CSRF header; and
- F passed: ordinary restoration, ordinary login, and an actual denied login retain
  their current behavior.

The suite uses deferred promises and `vi.waitFor` conditions for request counts and
rendered session state. It contains no fixed sleep, timeout increase, retry, or
network-idle readiness substitution.

### Owner and patch-shape decision

```text
PatchShape: request-generation guard at the existing transport completion boundary
CanonicalOwner: apps/frontend/src/api.ts authenticated transport
UpwardDrillSignal: yes — the Effect-level current flag guards its own then/catch, but
  api.ts publishes the 401 side effect first through mutable global transport state
Decision: fix owner; preserve AuthProvider and QueryClient ownership
Topology: single-root-multi-context (StrictMode restoration, different-user replacement,
  and same-user replacement are variants of the same stale unauthorized publication)
```

`api.ts` snapshots CSRF before dispatch but, after `globalThis.fetch` completes, invokes
whatever `unauthorizedHandler` is globally current at that later time. A later accepted
session reconfigures that global handler to clear the later session. The obsolete
request's 401 therefore invokes the later session's current handler before the
restoration Effect can apply its own `current` guard. Actor ID and callback identity do
not identify this boundary; B and C demonstrate why request/session generation is the
required identity. C deliberately accepts a later session for the same `user_id` with a
different transport generation, so its GREEN result cannot be implemented as an actor-
ID comparison.

### Deeper Cause Challenge

- Claimed cause: the authenticated transport does not bind unauthorized publication to
  the transport generation under which the request was dispatched.
- Causal status: root for the reproduced frontend defect class; not a proved attribution
  of the historical F-03 browser failure.
- Upstream generator: StrictMode and ordinary overlapping requests can leave an older
  request in flight while the existing owner accepts a later session. That overlap is a
  valid schedule, not an error to conceal.
- Recurrence path: old dispatch -> later transport/session configuration -> old 401 ->
  mutable current unauthorized handler -> later session cleared.
- Counterfactual intervention: permit unauthorized publication only when the request's
  transport generation is still current. The obsolete request still rejects to its
  caller, while only a current-generation 401 clears auth/CSRF/cache state.
- Plausible deeper candidate: backend cookie behavior, Vite proxying, or browser process
  lifecycle. Rejection evidence: A reproduces with controlled local deferred responses,
  no backend, cookie jar, Vite server, browser, or lifecycle process; the state change
  occurs synchronously through the real frontend transport/provider owners.
- Recurrence status: open before remediation; the planned owner guard closes this
  publication path for anonymous, different-user, and same-user replacement.
- Topology / anti-disguise proof: A, B, and C all converge on the same mutable handler
  read. D excludes stale restoration success as a second active mechanism in this
  experiment; E excludes globally ignoring 401 as an acceptable repair.

### Pre-Claim Gate Pass

```text
Topology: single-root-multi-context
CausalClosure: closed for the reproduced defect class from deferred response completion
  through api.ts unauthorized publication to AuthProvider clearSession and anonymous UI
Falsifier: if transport publication were already request-generation-bound, an obsolete
  401 would reject without changing the accepted session; A/B/C observed the opposite
SelfRefutation: direct context-driven replacement might bypass the visible login page,
  but A uses the real visible ordering (current anonymous restore, login success, then
  obsolete StrictMode restore) and fails by the same transport edge
LayerCeiling: L3 -> L4 unreachable for this defect class because the architecture already
  assigns one AuthProvider/transport lifecycle and requires stale-session isolation;
  no API, backend, cookie, Vite, or lifecycle policy change is needed to express it
Verdict: pass for the reproduced defect class
```

The historical first-run timeout remains **unattributed**. The deterministic test proves
that this frontend race can produce the same missing-authenticated-workspace symptom;
the prior guarded run contains no request-order timeline proving that this exact ordering
occurred. The report therefore distinguishes `reproduced defect class` from `historical
incident root cause still unknown`.

## Minimal remediation decision

The minimum production change is in `apps/frontend/src/api.ts` only: increment the
existing transport generation whenever authentication transport configuration changes,
capture that generation at request dispatch, and call the current unauthorized handler
only when the captured generation remains current at response completion. The API guard
suppresses only stale 401 side effects; it does not govern successful restoration
publication. `AuthProvider`'s existing Effect-local `current` flag remains the owner of
obsolete successful StrictMode restoration containment, as D1/D2 prove. This preserves
response parsing/rejection, current-session fail-closed handling, current CSRF behavior,
and all existing AuthProvider/query-clearing owners. `auth.tsx` needs no production edit
because the transport-generation fix closes the reproduced unauthorized side effect at
its actual owner.

## Remediation and regression result

`api.ts` now maintains one module-local authenticated-transport generation. Every call
to the existing `configureAuthenticatedTransport` advances it. Each real transport
request captures the generation before dispatch, continues to capture the then-current
CSRF value for its request, and invokes the centralized unauthorized handler only if
its captured generation still matches at response completion.

The stale response is not converted to success or hidden: it is still parsed and
rejected as the same `ApiError(401)` to its original caller. Only its obsolete global
side effect is suppressed. A current-generation 401 still invokes `clearSession`, which
cancels/clears the actual session QueryClient, removes the active CSRF value and handler,
and publishes anonymous state. No 401 is globally ignored.

The final focused suite contains seven condition-controlled actual-owner tests:

| Case | Final result | Proved boundary |
|---|---|---|
| A | PASS | StrictMode obsolete restoration 401 cannot clear the later login |
| B | PASS | old-session 401 cannot clear a later different-user session |
| C | PASS | old-session 401 cannot clear a later same-user session; generation, not actor ID, is decisive |
| D1 | PASS | obsolete successful StrictMode restoration cannot replace a later login; existing Effect guard owns success publication |
| D2 | PASS | obsolete successful StrictMode restoration cannot resurrect after logout |
| E | PASS | current-session 401 clears auth, the actual session QueryClient, and CSRF; the original request still rejects |
| F | PASS | normal restoration, normal login, and actual denied login remain correct |

The final focused command passed 7/7 in 112 ms. The first unmodified-production causal
run remains the RED evidence: A/B/C failed with `anonymous` after a later accepted
session, while the current-security and normal-path cases passed.

## Frontend state/cache and security review

**FRONTEND STATE/CACHE: PROCEED TO INDEPENDENT REVIEW**, subject to the predeclared
browser sequence that this writer was instructed not to run.

- Queries/consumers: no key, query function, consumer, filter, prefetch, stale-time,
  mutation, deletion, or invalidation contract changed.
- Key/team isolation: user/team/cache identities are unchanged. Same-user C proves the
  repair is not an actor-ID approximation of session identity.
- Session/401 lifecycle: a transport reconfiguration is the bounded session-generation
  boundary. Old requests cannot publish unauthorized effects into it; current requests
  retain the existing fail-closed owner.
- Cancellation/stale responses: current 401 still reaches `clearSessionQueries`; E
  inserts data into the provider's actual QueryClient and proves it is absent after the
  current 401. Stale unauthorized responses still reject but cannot clear later data.
- Mutations/retries/invalidation: unchanged. No automatic retry, optimistic auth update,
  fallback, or response replay was added.
- Deletion/anti-resurrection and performance: unchanged and covered by the preserved
  accepted UI tree/full frontend suite. This repair adds one integer comparison per
  completed response and no persistent storage.

**Integration/security self-review:** no active finding.

- CSRF remains attached only to unsafe requests from the value current at dispatch; E
  proves a current 401 removes it before the next unsafe request.
- Backend sessions, CSRF/origin enforcement, RBAC/team scope, safe 404 behavior, and
  authorization remain untouched and authoritative.
- No password, cookie, token, CSRF value, authorization header, request/response body,
  complete URL, KYC/PII, raw error, DOM snapshot, trace, video, HAR, or storage state is
  logged or retained by the diagnostic.
- No API protocol, shared model/type, backend route, schema, connector, configuration,
  dependency, business rule, mapping, provider status, persistence boundary, or
  architecture owner changed.
- Providers remain Mock/Local/Partial/Dormant exactly as recorded; no Live or approval
  claim was added.

## Verification evidence

| Check | Result |
|---|---|
| Causal RED on unmodified production owner | PASS as diagnostic evidence — A/B/C failed exactly on stale unauthorized publication; D/E/F passed |
| Final focused auth-ordering suite | PASS — 7/7 |
| Full frontend Vitest after final test content | PASS — 11 files, 212/212 tests; existing React Router SSR warnings only |
| Frontend typecheck after final test content | PASS |
| Frontend production build after final production change | PASS — Vite 7.1.11, 109 modules; JS 355.09 kB (103.23 kB gzip), CSS 61.04 kB (13.02 kB gzip) |
| Full backend pytest, first run | NON-PASS retained — 952 passed, 17 skipped, one live-memory HTTP seeder request timed out |
| Exact initially failed backend test | PASS alone in 3.31 s |
| Full backend pytest, final run | PASS — 953 passed, 17 skipped, 5 existing warnings in 124.92 s |
| Ruff | PASS |
| mypy | PASS — 91 source files |
| Canonical contract suite | PASS — 44/44 |
| Windows lifecycle, sandbox attempt | Missing permission — 4 passed/14 failed after owned-process termination returned `Access denied`; no product conclusion drawn |
| Windows lifecycle, permitted rerun | PASS — 18/18 in 334.575 s; owned processes stopped |
| Secret scanner | PASS |
| Secret-scanner unit tests | PASS — 8/8; pytest-cache permission warning only |
| Dependency integrity | PASS — no broken Python requirements |
| Architecture/project-state/tooling checks | PASS |
| Physical Mongo | Not applicable/not run — no persistence/schema/backend security owner changed |
| Single predeclared implementer guarded browser suite | PASS — exactly one run, 3/3 tests in 8.1 s using one worker; no retry |
| `pre_pr_check.py` | Not run — publication is prohibited and the clean committed-tree prerequisite is absent |

The full backend rerun and lifecycle suite preserve the accepted POC regression and
process/session security surfaces. The initial backend timeout and sandbox lifecycle
failures are retained above; later green evidence does not erase them.

### Single guarded browser run

The coordinator subsequently authorized the implementer's one predeclared guarded
browser run on the frozen candidate. It was executed exactly once and sequentially,
including the ordinary runner-managed startup, with no retry:

```text
.venv\Scripts\python.exe scripts\run_e2e.py --backend-port 8867 --frontend-port 4275
```

The runner's existing sanitized output reported all three Playwright tests passing on
one worker in 8.1 seconds: real-login protection, the Singapore clean Mock target path,
and authoritative document-review progression with read-only superseded history. Its
final legacy summary line still says `2 authenticated local Mock smoke tests`; the
authoritative Playwright result immediately above it is 3/3, and this bounded diagnosis
did not modify the runner. The runner cleaned up its owned processes: no listener
remained on 8867 or 4275 after completion.

The browser run tested the frozen production/test content identified by these hashes:

```text
477e06dfa2abf5ba190ab5e70842e4d23a91950787b6f8f48ff94958b5112a00  apps/frontend/src/api.ts
49f85aa627c09134fe2f8ec8611cf59ef5187dca7d13131f390aa326665bbc0b  apps/frontend/src/AuthSessionOrdering.test.tsx
```

This green acceptance run increases confidence in the frozen candidate but does not
retroactively prove why the historical browser run failed: that run still lacks the
request/response ordering evidence required to attribute it to the reproduced race.

## Content identity, hygiene, and handoff

Final changed implementation/test hashes used by the evidence above:

```text
477e06dfa2abf5ba190ab5e70842e4d23a91950787b6f8f48ff94958b5112a00  apps/frontend/src/api.ts
49f85aa627c09134fe2f8ec8611cf59ef5187dca7d13131f390aa326665bbc0b  apps/frontend/src/AuthSessionOrdering.test.tsx
```

The diagnostic/remediation writer changed only:

- `apps/frontend/src/api.ts`;
- `apps/frontend/src/AuthSessionOrdering.test.tsx`; and
- `.ai-pipeline/reports/REVIEW_REWORK_UI_AUTH_DIAGNOSIS.md`.

All previously accepted UI implementation paths remain byte-identical to section 18 of
the final historical quality-gate manifest. `git diff --check` passes for tracked
changes; the two task-owned new files have no trailing whitespace and have final
newlines. No relevant listener remains on ports 8000, 5173, 8867, or 4275. No file was
staged, committed, pushed, merged, reset, stashed, or published; `git clean` was not
used.
The secret-unit run's inaccessible task-created pytest-cache directory was verified as
inside this repository and removed explicitly; no product or user-owned path was
deleted.

## Bounded H-01 Markdown whitespace remediation evidence

Date: 2026-09-20<br>
Role: bounded docs-only mechanical remediation writer<br>
Classification: `DOCS_ONLY`; no browser or full regression rerun

The separate independent authentication/security re-quality gate returned `PASS WITH
MINOR FIXES` solely for H-01. This remediation changed no product, authentication,
cache, security, API/model/type, schema, connector, configuration, business rule,
mapping, architecture, provider status, finding wording, date, or verdict history.

| Normalized file | Original SHA-256 | Normalized SHA-256 |
|---|---|---|
| `.ai-pipeline/001_planner/REVIEW_REWORK_UI_EXECUTION_ADDENDUM.md` | `101828e18d25eeb11fc80b9cc934b7db4dfef9666aaf394261b50951ee26e01d` | `96f11d53347263af6bc89e2a67f2f2f53fefed272ad8d9bf7e06435a331da273` |
| `.ai-pipeline/reports/REVIEW_REWORK_UI_IMPLEMENTATION.md` | `1556f4b92b1460088012192a9df62b9b01e91bf48adbbd9253ff077761f2deb7` | `fe4d52ea5bb2790f45a049de365ecff14fe4fc930c82b1aa71a68bf930280cc3` |
| `.ai-pipeline/reports/REVIEW_REWORK_UI_QUALITY_GATE.md` | `fc3b83cde150ea11cb79803fb3585dca82ed80e8931511c661034281f7354ae5` | `6ff739659b46565e95071d5ae872a8ad45372692e8164eefb6968abde639b3e5` |

Exact mechanical transformations, using line numbers before the edits:

- execution addendum lines 3-6: replaced only the terminal two-space Markdown hard
  break on each line with `<br>`; removed only the extra blank EOF line 121 while
  retaining one final LF;
- implementation report lines 3-4: replaced only the terminal two-space Markdown hard
  break on each line with `<br>`; and
- historical quality-gate report lines 3-4, 107, 124, 141, 163, 258-259, and 442-443:
  replaced only the terminal two-space Markdown hard break on each line with `<br>`.

Hygiene evidence:

- `git diff --check` emitted no whitespace error and exited `0`; existing line-ending
  notices only;
- `git diff --no-index --check -- NUL <path>` for each normalized untracked file emitted
  no whitespace error; exit `1` records the expected content difference from `NUL`;
- a byte/regex audit found zero trailing-whitespace lines in every normalized file,
  exactly one final LF, and no extra blank EOF; and
- SHA-256 reconciliation against the fresh authentication gate passed for all eleven
  production/test paths in its frozen manifest: `api.ts`,
  `AuthSessionOrdering.test.tsx`, and the nine product/test paths retained from section
  18 of the historical gate. The twelve-row historical section-18 manifest was also
  reconciled: its three authorized documentation rows changed only as recorded above,
  while all nine production/test rows remain byte-identical.

No file was staged, committed, pushed, merged, reset, stashed, cleaned, or published.
Publication remains blocked. The frozen remediation handoff is these three normalized
documents plus this appended evidence section; a fresh independent exact `PASS` is
still required before any publication role may proceed.

## Result and remaining uncertainty

- Root cause for the reproduced defect class: **reproduced and remediated**.
- Root cause of the historical first guarded browser timeout: **still unknown**. The
  historical run lacks the bounded request/response order needed to attribute it to this
  race.
- Closed UI findings F-01, F-02, and F-04 and the accepted F-03 product assertions:
  preserved unchanged.
- Remaining required action: the frozen candidate is ready for a fresh independent High
  authentication/security reviewer to perform three sequential fresh full runs and issue
  the separate `REVIEW_REWORK_UI_AUTH_REQUALITY_GATE.md` verdict. Publication remains
  blocked until exact independent `PASS`.
