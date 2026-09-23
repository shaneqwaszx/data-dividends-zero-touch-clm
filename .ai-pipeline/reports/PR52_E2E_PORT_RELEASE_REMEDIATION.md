# PR #52 E2E Isolation / Socket-Lifecycle Remediation

Date: 2026-09-22

Branch: `integration/acra-teammate-reconciliation`

Base and current `origin/main`: `ef338c9b7926a298e8987acb975fd93c96ed2bfb`

Published parent / PR head: `5ad738af2a07c6fc28ed379104079abeb2fa91a3`

Change class: `CI_TOOLING` with supporting tests and this report.

Current status: **CANDIDATE READY FOR INDEPENDENT QUALITY GATE**. The historical stops
below remain chronological evidence. The final bounded remediation removes redundant
two-case workload from the representative-routes selector while preserving the real
two-case route transition as its own focused selector; the final verification is green.

## Chronology and Preserved Historical Evidence

### 1. Original PR head `cff6e2f...`

- Push run `35720468238` and pull-request run `35725121231` both failed E2E.
- In both runs lifecycle 1/7 passed, then lifecycle 2/7 failed the strict pre-start raw
  bind proof with `OSError: [Errno 98] Address already in use`.
- Those runs remain failures and are not relabelled.

### 2. Published first remediation `5ad738af...`

- The first remediation added a strict post-shutdown wait for the same backend/frontend
  port pair, capped at 10 seconds.
- Fresh push run `35731638001` and pull-request run `35731643853` both failed E2E after
  lifecycle 1 passed because ports 8765/4173 did not become strictly bindable within the
  cap.
- Push run `35731638001` also had one Windows
  `test_start_stop_health_pids_and_unrelated_processes` frontend-proxy login timeout;
  the same Windows job passed in pull-request run `35731643853`.
- Backend, frontend, security, and phase12-mongo passed in both fresh runs.

### 3. Diagnostic refinement

The fresh Linux CI proves only that a strict raw Python bind to the old tuple remained
unavailable for more than 10 seconds. It does **not** distinguish:

- a task-owned listener/descendant that survived cleanup;
- kernel/TCP socket state incompatible with the strict bind after listener exit; or
- both.

Therefore the lower mechanism remains `deepest-confirmed-root-unknown`. The proved
runner design defect is the coupling of otherwise isolated selections to immediate
reuse of one TCP pair, with old-tuple bindability treated as a cleanup invariant.

### 4. Preserved second-cycle dirty experiment

The three reported unstaged changes contained only:

- `PORT_RELEASE_TIMEOUT_SECONDS` increased from 10 to 75 seconds;
- the default suite timeout increased from 240 to 900 seconds;
- one timeout-oriented unit test and report text claiming retained Linux socket state.

The exact binary patch was saved before supersession at:

`C:\Users\shane\Desktop\FYP\PR52-second-cycle-dirty-experiment.patch`

The timeout increase and unsupported lower-mechanism claim were deliberately removed.
No reset, rebase, stash, clean, or broad checkout was used.

The experiment also observed a local timeout involving
`/api/clm/zero-touch/case-portfolio` in the Singapore clean-fixture test. On the final
runner design that exact test passed in four complete suites and the earlier specific
failure did not reproduce. No case-portfolio or other product code was changed.

## Final Runner Design Candidate

### Process ownership and exit proof

- `OwnedProcess` records the exact POSIX process-group ID created by
  `start_new_session=True`.
- POSIX cleanup sends bounded TERM, then bounded KILL if required, waits for the parent,
  and uses stdlib `killpg(group, 0)` polling to prove the exact owned group is absent.
- A surviving owned group after TERM/KILL fails cleanup.
- Windows keeps the existing owned-process `CTRL_BREAK_EVENT` then exact
  `taskkill /PID <owned-pid> /T /F` behavior and positively checks parent termination.
- Every started process is still stopped in reverse order; one cleanup failure does not
  prevent attempts to stop the other task-owned processes, and the lifecycle fails
  closed.
- No process enumeration, `pkill`, `netstat`, `lsof`, `ss`, or unrelated-process kill
  path was introduced.

### Deterministic lifecycle ports

One helper, `_allocate_lifecycle_ports`, derives all pairs from the configured base pair:

- selection 0 receives the configured base pair;
- selection `n` receives `(backend_base + n, frontend_base + n)`;
- all ports must remain within 1024..65535;
- backend/frontend and cross-selection collisions fail closed;
- selection count and base values are validated;
- no pair is reused within the suite; and
- allocation is deterministic and non-random.

Every lifecycle still invokes the unchanged strict `_assert_ports_available()` before
starting any process on its new pair. The currently published post-shutdown strict-bind
wait is retired: cleanup proves owned-process exit, while the next lifecycle proves its
own fresh pair is available before startup. No `SO_REUSEADDR` bypass was added.

Each backend, Vite proxy, and Playwright process receives origins derived from that
selection's pair. Selector discovery remains dynamic; no test count is hard-coded.

## Test-First and Focused Evidence

- RED: `python -m unittest tests.test_run_e2e -v` against the restored published
  baseline produced 1 failure and 16 errors across the newly added port-allocation,
  cleanup, isolation, and process-ownership tests.
- Final focused run: `python -m unittest tests.test_run_e2e -v` — **31/31 PASS**.
- `python -m ruff check scripts/run_e2e.py tests/test_run_e2e.py` — **PASS**.

Focused coverage includes:

- base-pair selection and deterministic unique subsequent pairs;
- backend/backend, frontend/frontend, and cross-role collision prevention;
- lower/upper bounds, overflow, malformed bases, and dynamic selection count;
- occupied fresh lifecycle port failing before process startup;
- old-port non-bindability not overriding successful owned-process cleanup;
- strict socket-probe closure;
- correct per-pair backend, frontend-proxy, and Playwright origins;
- reverse cleanup, cleanup failure reporting, and fail-closed result;
- POSIX TERM/KILL group ownership and surviving-group failure;
- exact Windows owned-PID tree termination command; and
- dynamic selector discovery and fail-fast behavior.

## Browser and Windows Lifecycle Evidence

The first sandboxed browser attempt was blocked before browser startup by local
`esbuild` `spawn EPERM`. The identical permitted command was then used.

Complete `python scripts/run_e2e.py` observations during this candidate cycle:

1. **PASS — 7/7** dynamically discovered isolated lifecycles.
2. **PASS — 7/7** dynamically discovered isolated lifecycles.
3. **FAIL — selection 3/7**: unchanged document-review UI did not show
   `3 final / 4 fields` within 30 seconds. Three immediate isolated reruns of that
   unchanged test on fresh explicit port pairs all passed.
4. **PASS — 7/7** dynamically discovered isolated lifecycles.
5. After the last allocator-validation/test-only refinement, **FAIL — selection 7/7**:
   unchanged responsive test timed out after 120 seconds waiting for an accepted case
   status. An immediate standalone rerun on fresh ports failed the same responsive test
   at login after 30 seconds.

No complete run failed due to port allocation, old-port bindability, process cleanup,
or lifecycle 2 reuse. However, the responsive test is now a repeated product-facing
failure on the exact executable candidate, so the assignment's stop condition applies.

`python -m unittest tests.test_demo_lifecycle_windows -v` — **23/23 PASS** in
423.867 seconds. The exact historically intermittent
`test_start_stop_health_pids_and_unrelated_processes` test passed locally unchanged.
No Windows lifecycle implementation change was made.

## Product Freeze and Scope

- Changed implementation/test/report paths are limited to `scripts/run_e2e.py`,
  `tests/test_run_e2e.py`, and this report.
- No ACRA, Garden Business, BizFile, jurisdiction, ownership/UBO, Mongo, priority,
  policy, frontend business behavior, case-portfolio behavior, provider readiness,
  API/model/type, schema, connector, mapping, authentication, or product configuration
  was changed.
- No Phase 22 work was performed.
- No timeout inflation, random port, port-reuse option, broad kill, test skip, test-count
  reduction, or unconditional sleep was introduced.

## Blocker and Next Authorized Action

The deterministic-port/process-ownership candidate is focused-green and repeatedly
demonstrated that the historical Linux old-port reuse failure is absent. It cannot yet
receive the required independent `PASS` because the exact candidate does not currently
have a passing complete browser suite: the unchanged responsive test failed twice with
product-facing timeouts.

Per the assignment, this finding is not remediated inside the CI-tooling task. Required
next action is a separately authorized diagnosis of the responsive/product timing
failure, followed by a fresh complete E2E pass on this runner candidate. Only then may
the candidate be frozen for independent quality gate, commit, push, and fresh push/PR
CI.

No independent final quality gate, commit, push, PR-body mutation, merge, or Phase 22
work was performed in this cycle.

## Responsive/Product Timing Diagnosis

### Preserved state and exact failing assertions

The diagnosis began at published `HEAD` `5ad738af2a07c6fc28ed379104079abeb2fa91a3`
and tree `2970dbbc0b664040072b15489e267680e78b4a2d`, with current
`origin/main` `ef338c9b7926a298e8987acb975fd93c96ed2bfb`. The only dirty paths
were this report, `scripts/run_e2e.py`, and `tests/test_run_e2e.py`. Before diagnostic
instrumentation, the binary candidate diff identity from
`git diff --binary ... | git hash-object --stdin` was
`ee5f7fbe1308d6e30b6484af1885bd13c8056046`.

The reported "responsive test" is
`apps/frontend/e2e/responsive-layout.e2e.ts:202`, titled
`responsive shell contains primary screens, account hover, forms, tables, and dialogs`.
The two historical assertion sites are:

- Final complete run: `waitForCaseStatus` at original lines 177-182, where
  `expect.poll` issues same-origin
  `GET /api/clm/zero-touch/cases/{opaque-case-id}` requests for up to 120 seconds and
  expects the clean case to reach `COMPLETED`.
- Immediate isolated rerun: `login` at original lines 43-50, where clicking `Sign in`
  is followed by a 30-second assertion that the `Main workspace` navigation is visible.

The historical output retained before this diagnosis does not contain request-level
timelines for those two runs, so their missing events must not be inferred beyond the
exact assertions above.

### Temporary safe observability and bounded repetitions

Temporary instrumentation recorded only monotonic elapsed time, HTTP method, sanitized
route path, HTTP status, cookie presence as a boolean, current status enum, and page path.
It recorded no bodies, credential, cookie value, session/CSRF value, document content,
case detail, or provider payload. A temporary 30-second Python thread-stack watchdog was
also used for one neighboring run. All temporary instrumentation was removed before this
report was finalized.

Five responsive repetitions used clean isolated lifecycles and distinct deterministic
port pairs:

| Run | Backend/frontend | Result | Elapsed | Safe outcome |
|---|---:|---|---:|---|
| 1 | `8765/4173` | PASS | 22.170s | login 200; both case paths reached their accepted statuses |
| 2 | `8766/4174` | PASS | 22.269s | same |
| 3 | `8767/4175` | PASS | 22.822s | same |
| 4 | `8768/4176` | FAIL | 131.460s | clean-case upload dispatched but never completed; case remained `PENDING_INPUTS` |
| 5 | `8769/4177` | PASS | 21.057s | login 200; both case paths reached their accepted statuses |

In failing run 4, readiness and authentication succeeded first: frontend `/` was ready;
two initial `/api/auth/me` requests returned expected unauthenticated 401; the browser
dispatched `POST /api/auth/login`; it returned 200 with a session cookie present; the
workspace rendered at `/dashboard`; and dashboard, portfolio, and execution-profile
proxy requests returned expected statuses. Case creation then returned 201. The browser
dispatched
`POST /api/clm/zero-touch/cases/{opaque-case-id}/intake/documents`, but no response was
observed. Status polls 1-27 each returned HTTP 200 in 24-40ms with
`status=PENDING_INPUTS`. Poll 28 did not complete for approximately 94 seconds, and the
120-second predicate expired. This proves request dispatch plus missing response
completion for the upload path; it does not prove whether the deepest blocker was
browser/Vite request-body transport, backend body intake, or a later in-process step.

Three additional clean-fixture lifecycles on `8790/4200`, `8791/4201`, and `8792/4202`
all passed in 6.8-7.0s of Playwright test time. Therefore the upload symptom is
intermittent, not a deterministic clean-lifecycle product defect.

### Readiness, port propagation, and process evidence

The reproduced failure rules out backend-health-only or frontend-root-only readiness as
the missing event for that occurrence: the same-origin Vite proxy completed login,
session bootstrap, dashboard/portfolio, execution-profile, case creation, and 27 case
reads before the upload/status path stalled. Five initial responsive logins all completed
normally during this diagnostic sample, so the earlier standalone login timeout did not
reproduce and remains unclassified.

Repository search and the runner/unit-test owner confirm each derived pair flows through:

- backend `CLM_E2E_BACKEND_PORT` and `CLM_E2E_FRONTEND_ORIGIN`;
- Vite `--port` and `VITE_BACKEND_PROXY_TARGET`;
- Playwright `PLAYWRIGHT_BASE_URL` and `CLM_E2E_BACKEND_ORIGIN`; and
- the browser network policy constructed from those exact Playwright origins.

The only `8765`/`4173` occurrences on the relevant runtime path are runner defaults,
Playwright's local default, and explicit unit-test fixtures/assertions. No hidden runtime
consumer of the original base pair was found. Every diagnostic failure occurred on its
reported derived pair rather than the base pair.

After the responsive failure, an elevated read-only Windows process query filtered to
this exact repository path found zero matching Python, Node/Vite, Playwright, or Chromium
processes. The check does not prove transient resource pressure during execution, but it
does falsify a surviving task-owned process after that failed lifecycle. No historical
port-reuse or cleanup failure recurred.

### Neighboring selectors

| Selector | Ports | Result | Evidence |
|---|---:|---|---|
| protected login | `8780/4190` | PASS | 2.9s Playwright time |
| Singapore clean fixture | `8781/4191` | PASS | 8.9s Playwright time |
| document review | `8782/4192` | FAIL | backend reached two final fields, but UI stayed at the prior one-field presentation for 30s |

The document-review failure occurred at original lines 308-321: after the test clicked
the legal-name review action, its direct backend poll proved two non-pending fields, but
the next UI assertion could not find `2 final / 4 fields`. The temporary stack watchdog
showed the backend event loop polling normally and AnyIO worker threads idle during that
UI wait. This is evidence of a frontend query-refresh/test-synchronization symptom,
separate from the responsive upload request that never completed. It also independently
repeats the previously observed document-review failure class, so it cannot be dismissed
as a passing neighboring control.

### Classification and stop decision

- `A` backend not ready despite `/health`: **not supported** for the reproduced failure.
- `B` Vite proxy not operational: **falsified** for the reproduced failure by completed
  auth/bootstrap/case requests through the same proxy.
- `C` login/auth bootstrap not ready: the historical isolated symptom did not reproduce;
  all five diagnostic responsive logins and the protected-login neighbor passed.
- `D` backend returned an error/timeout: no error response was returned for the failing
  upload; completion was absent.
- `E` browser request never dispatched: **falsified** for the upload failure.
- `F` request dispatched but response never completed: **proved** for the upload failure.
- `G` listener attached after the event: **falsified** for the status-poll failure, which
  used repeated direct requests rather than a one-shot listener.
- `H` test/query race: **supported for the separate document-review UI failure**, but not
  for the responsive upload failure.
- `I` cross-lifecycle task-owned process leak: **not supported after failure**; zero exact
  repository-owned processes remained. Transient non-process resource pressure is not
  proved or excluded.
- `J` deterministic application defect: **not proved**; four of five responsive runs and
  four consecutive clean-fixture executions passed.
- `K` deepest confirmed mechanism: an intermittent same-origin clean-document upload can
  be dispatched without response completion, leaving the case `PENDING_INPUTS`; the
  browser/Vite-body-versus-backend-intake boundary remains unresolved.

The owner classification is therefore `deepest-confirmed-root-unknown`, not runner,
test, or product conclusively. The responsive occurrence crossed the browser/Vite/backend
boundary, while the document-review neighbor separately exposed a likely test/query
synchronization defect. Applying a runner readiness change would not address an upload
that fails after successful authentication and case traffic. Timeout inflation, retry,
test weakening, and product edits are unsupported.

The exact candidate is not quality-gate eligible: a responsive product-facing failure
reproduced once in five runs, the document-review neighboring selector failed again, and
neither recurrence generator is closed. No candidate fix, independent quality gate,
commit, push, merge, or Phase 22 work was performed. The next bounded action is a
separate instrumented browser/Vite/backend upload-transport investigation that captures
request-body completion and backend request-entry/body-read milestones, plus an
independent test-synchronization remediation for the document-review query refresh.

## Upload Boundary Investigation

Date: 2026-09-23

### Exact request-path ownership

The current successful raw-body path is:

1. browser `File` retained by `apps/frontend/src/App.tsx`;
2. `intakeZeroTouchDocument` in `apps/frontend/src/api.ts`, which sends the `File` as
   the request body rather than multipart/form-data;
3. same-origin `/api` proxy in `apps/frontend/vite.config.ts` targeting the exact
   lifecycle-derived backend origin;
4. FastAPI route `intake_zero_touch_document` and helper
   `intake_zero_touch_document_request` in `apps/backend/app/main.py`;
5. bounded Starlette `request.stream()` consumption in `_read_bounded_body`;
6. `ZeroTouchOrchestrator.intake_document` and the existing document-processing owner;
7. `DocumentProcessingResponse` serialization and the same proxy/browser response path;
8. later explicit `/intake/complete` orchestration transition owned by the existing
   frontend intake flow and backend zero-touch orchestrator.

There is no multipart parser or `UploadFile` on this route. Size enforcement occurs
first against a valid declared `Content-Length` and again cumulatively while reading
the request stream. Uploaded bytes remain transient.

### Safe milestone seam

The runner now offers explicit `--diagnostics` mode. Normal runs do not receive its
environment variables. Diagnostic mode adds one per-upload UUID and emits only the
approved method, sanitized route family, case UUID, integer content length when
available, milestone, status, elapsed/monotonic time, PID, and derived port. It emits no
document content, extracted text, filename, multipart body, credential, token, cookie,
CSRF value, provider payload, or private error detail. Focused tests prove the backend
seam is disabled by default and excludes the supplied private filename, while runner
tests prove diagnostic variables are explicit.

The Vite seam records request acceptance, upstream start, outgoing-request completion,
upstream response headers, and response completion. The backend seam records route
entry, raw-body read start/complete, document-service start/complete, and response
return. The browser records dispatch, response headers, and response-body completion.

### Corrected diagnostic execution and stop

The first attempted diagnostic execution on `8865/4273` was invalid evidence for the
product path: the task-owned backend launcher had deliberately cleared the inherited
validated backend-port environment value, while the new logger attempted to read it.
That diagnostic-only defect produced HTTP 500 before a backend milestone. The launcher
was corrected to retain the already validated derived port only in diagnostic mode;
Ruff, backend document tests, and runner tests then passed before browser execution was
restarted from run 1.

The corrected responsive run used backend/frontend `8870/4280`. Both uploads completed
the entire traced path:

| Upload | Browser | Vite | Backend | HTTP result |
|---|---|---|---|---|
| clean fixture | dispatch -> headers -> body complete | accepted -> upstream started -> outgoing body complete -> response -> response complete | entered -> body read start/complete -> service start/complete -> response returned | `201` |
| low-confidence fixture | dispatch -> headers -> body complete | accepted -> upstream started -> outgoing body complete -> response -> response complete | entered -> body read start/complete -> service start/complete -> response returned | `201` |

The clean case subsequently reached `COMPLETED` and the low-confidence case reached
`WAITING_FOR_REVIEW`, because the responsive selector advanced beyond both
`waitForCaseStatus` calls. The run then failed at the later logout helper: after the
Sign out click, the `Sign in` heading did not appear within 15 seconds. No upload retry,
duplicate POST, timeout increase, direct-backend browser call, or workflow change was
introduced.

Per the assignment's failure rule, the matrix stopped immediately after this corrected
run rather than continuing to runs 2-5. The exact responsive selector still has a
product-facing failure while the historical intermittent upload recurrence generator
has not been captured at a deeper failing milestone.

Upload outcome:

- corrected reproduction count: `1` responsive execution before mandatory stop;
- uploads observed: `2`, both complete through `BACKEND_RESPONSE_RETURNED` and
  `BROWSER_UPLOAD_RESPONSE_COMPLETE` with `201`;
- deepest completed boundary for this run: browser response body complete;
- deepest historical failing boundary: browser dispatch only, with Vite/backend
  receipt still unknown for that earlier occurrence;
- root classification: `deepest-confirmed-root-unknown` for the historical upload hang;
- current stop trigger: separate later logout/render failure in the exact responsive
  selector.

## Document Review Query Synchronization

### Proven synchronization defects

`CaseDetail` remains the sole mutation, query-cache, and authoritative-refresh owner;
`DocumentEvidencePanel` remains presentation and ephemeral form state only. The existing
keys remain actor/case scoped:

- `['auth', userId, 'cases', 'detail', caseId]`;
- `['auth', userId, 'cases', 'documents', caseId]`;
- `['auth', userId, 'cases', 'ownership', caseId]`.

Focused adverse tests proved two related defects in the existing manual authoritative
refresh:

1. `OTHER_PROVED / AUTHORITATIVE_REFRESH_HEAD_OF_LINE`: `refreshEvidence` awaited the
   detail, documents, and ownership GETs in one `Promise.all` and published none until
   all completed. A fresh documents response could therefore contain the reviewed
   field while an unrelated ownership response remained pending, leaving the query
   cache and rendered count stale.
2. `STALE_RESPONSE_RACE`: an older in-flight exact documents query could complete after
   the manual authoritative publication and overwrite the newer reviewed document
   state.

This accounts for the historical browser observation without calling it a test-only
race: backend authoritative GET count was `2`, rendered count remained `1`, and the old
implementation supplied no deterministic guarantee that the fresh documents result had
been published without an unrelated wait or later stale overwrite.

### Minimal owner correction

Before an evidence refresh, `CaseDetail` now awaits cancellation of only the existing
exact actor/case detail, documents, and ownership queries. It then starts the same three
authoritative GETs and publishes each result independently as it completes, subject to
the unchanged generation/case/actor guard. The mutation remains serialized until the
full refresh settles; refresh failure still blocks subsequent mutation where required.

No query key, QueryClient, retry policy, session/logout/401 clearing, browser storage,
authorization owner, backend contract, document rule, or business workflow changed.

Focused regression evidence:

- late prior documents completion cannot replace the reviewed result;
- a fresh reviewed documents response renders before an unrelated ownership refresh
  completes;
- same-tick duplicate review remains one POST;
- previous-case and previous-actor completions remain contained;
- review failure cannot falsely advance the visible count;
- targeted retry/re-upload and historical replacement behavior remain covered;
- the existing browser test was changed to register mutation and documents-response
  expectations before each click and to check the exact `1 -> 2 -> 3 -> 4` sequence;
- diagnostic browser logging records mutation dispatch/completion, authoritative
  documents GET count, query-cache publication count, and rendered count without field
  values.

Fresh focused results on the current dirty candidate:

| Check | Result |
|---|---|
| `python -m unittest tests.test_run_e2e -v` | PASS — 32/32 |
| backend document API/processing focused pytest | PASS — 63/63 |
| focused Phase 15C navigation + document panel Vitest | PASS — 51/51 |
| frontend TypeScript check | PASS |
| focused Python Ruff | PASS |
| `git diff --check` before this report append | PASS |

The post-fix document-review browser selector was not run because the earlier corrected
responsive selector triggered the assignment's mandatory stop. Therefore the focused
fix is not browser-verified, the document-review lane is not completion-eligible, and no
independent quality gate may run.

## Diagnostic Stop Receipt

- Runner candidate: deterministic unique port pairs, strict pre-start bindability,
  exact owned-process cleanup, no random ports, no reuse bypass, and no broad kill remain
  intact; focused runner suite is green.
- Scope: no ACRA, Garden Business, BizFile, ownership/UBO, Mongo, priority, policy,
  GoldTier, provider-readiness, business-rule, or Phase 22 change.
- Git: no commit, push, PR mutation, merge, or independent quality gate.
- Required next bounded action: independently diagnose the later responsive logout
  failure, then restart the upload matrix from run 1; if responsive becomes repeatedly
  green, run the instrumented document-review selector at least three consecutive times
  before any complete-suite or QG work.

## Responsive Logout Diagnosis and Restarted Upload Matrix

Date: 2026-09-23

### Direct isolated logout reproduction

A temporary condition-synchronized Playwright selector exercised only:

`login -> Main workspace visible -> account menu -> Sign out -> anonymous Sign in`

It registered the logout request and response conditions before the click and recorded
only the fixed method/route family, response status, sanitized page path, inferred
authenticated/anonymous state, relevant in-flight API request counts, browser-page
liveness, render milestone, and elapsed milliseconds. It emitted no credential, cookie,
session value, CSRF value, case payload, or response body. The temporary selector and
logout instrumentation were removed after the bounded diagnostic; no non-reproducing
logout behavior was changed and no new timeout, sleep, reload, or retry remains.

| Cycle | Backend/frontend | Result | Request | Response | Anonymous render | Elapsed |
|---|---:|---|---|---|---|---:|
| 1 | `8890/4300` | PASS | dispatched | `204` | Sign in visible | `153 ms` |
| 2 | `8891/4301` | PASS | dispatched | `204` | Sign in visible | `141 ms` |
| 3 | `8892/4302` | PASS | dispatched | `204` | Sign in visible | `126 ms` |
| 4 | `8893/4303` | PASS | dispatched | `204` | Sign in visible | `149 ms` |
| 5 | `8894/4304` | PASS | dispatched | `204` | Sign in visible | `156 ms` |

Cycles 1-4 observed zero relevant API queries during the logout boundary. Cycle 5
observed two relevant API requests with a peak of one active request; both settled by
logout dispatch and did not delay the `204` response or anonymous render. Every cycle
remained at `/dashboard`, the browser page remained open through the render milestone,
and the runner completed exact owned-process cleanup. The historical responsive logout
failure is therefore classified `TRANSIENT_NON_REPRODUCIBLE`: the request-not-dispatched,
request-hung, completed-response/stale-UI, auth stale-response, cache head-of-line,
router-render, and test-wait-order mechanisms were not reproduced in this bounded
sample. This is not a claim that no latent mechanism exists.

The first restricted lifecycle attempt was blocked before browser startup by the known
local Vite/esbuild `spawn EPERM` sandbox restriction. It is missing-infrastructure
evidence only. One permitted invocation used an over-anchored grep that selected no
test; it is command-shape evidence only. Neither is counted among the five cycles above.

### Responsive/upload matrix restarted from run 1

The exact responsive selector was restarted from run 1 with the existing safe upload
milestones and temporary logout milestones enabled. Each run used a clean isolated
lifecycle and a distinct deterministic port pair.

| Run | Backend/frontend | Upload HTTP result | Accepted case-status result | Logout result | Final result |
|---|---:|---|---|---|---|
| 1 | `8900/4310` | both `201`, browser response complete | clean `COMPLETED`; low-confidence `WAITING_FOR_REVIEW` | three `204` responses and anonymous renders | PASS |
| 2 | `8901/4311` | both `201`, browser response complete | clean `COMPLETED`; low-confidence `WAITING_FOR_REVIEW` | three `204` responses and anonymous renders | PASS |
| 3 | `8902/4312` | both `201`, browser response complete | clean `COMPLETED`; low-confidence `WAITING_FOR_REVIEW` | three `204` responses and anonymous renders | PASS |
| 4 | `8903/4313` | both `201`, browser response complete | clean `COMPLETED`; low-confidence `WAITING_FOR_REVIEW` | three `204` responses and anonymous renders | PASS |
| 5 | `8904/4314` | both `201`, browser response complete | clean `COMPLETED`; low-confidence `WAITING_FOR_REVIEW` | first `204` response and anonymous render passed | FAIL |

All ten uploads reached browser dispatch, Vite request acceptance/upstream completion,
backend request entry/body-read completion/document-service completion/response return,
Vite response completion, and browser response-body completion with HTTP `201`. No
upload was retried and no timeout was increased. This bounded matrix therefore contains
no upload hang, but the historical intermittent upload recurrence generator remains
`deepest-confirmed-root-unknown`; successful samples alone do not close it.

Responsive run 5 progressed beyond both accepted case statuses and its first logout.
After the subsequent Ethan Tan login and policy/case-dialog checks, `page.goto` for the
review case returned, but the `Document evidence and review` heading did not render
within the existing 15-second assertion. The deepest confirmed failing boundary is the
case-detail navigation/query/render boundary; no safe request/query milestone was
present to prove a deeper owner, so its classification remains
`DEEPEST_CONFIRMED_ROOT_UNKNOWN`. Both assigned ports were strictly bindable after the
failed lifecycle, proving cleanup completed.

### Stop decision

The responsive matrix is `4/5`, so the assignment's stop rule applies. The document-
review `3/3` browser matrix, neighboring selectors, two complete E2E suites, Windows
lifecycle, broad final verification, independent quality gate, commit, push, PR update,
and fresh CI were not run. The current CaseDetail fix remains focused-test green but not
browser-accepted.

The next bounded action is an instrumented diagnosis of the run-5 case-detail
navigation/query/render failure, capturing sanitized route entry, exact actor/case query
dispatch/completion/publication, active auth state, and rendered view state without
retrying or weakening the selector. No ACRA, Garden Business, BizFile, provider,
business-rule, persistence, schema, API/model/type, mapping, or Phase 22 behavior
changed.

Post-stop verification retained the task boundary: `python -m unittest
tests.test_run_e2e -v` passed `32/32`; `git diff --check` passed; the explicit report
trailing-whitespace scan found no matches; and the responsive E2E file contains only
the previously retained diagnostic-console forwarding delta. No temporary logout
selector or logout instrumentation remains.

## Case-detail Navigation / Query / Render Diagnosis

Date: 2026-09-23

### Exact historical boundary

The failed responsive action was the direct navigation at
`apps/frontend/e2e/responsive-layout.e2e.ts:315`:

`page.goto(/cases/{opaque-case-uuid})`

The expected URL and observed pathname were the same opaque case-detail route. The
existing heading assertion at line 316 then waited for `Document evidence and review`
and timed out after 15 seconds. The historical run had no case-detail request, query,
cache-publication, or render-state milestones, so it could not support a deeper causal
claim.

### Bounded diagnostic method

A temporary exact Playwright selector exercised the same business path and actor
transition:

`Maya login -> low-confidence intake -> WAITING_FOR_REVIEW -> logout -> Ethan login -> direct page.goto(case detail) -> review heading/action visible`

Temporary diagnostics recorded only monotonic time, synthetic actor ID, opaque case
UUID, route path/family, request dispatch/completion/status, abort category, query
status/publication, component mount/unmount, generation, and render-state enum. They
did not record credentials, cookies, CSRF values, document content, legal names,
addresses, raw case/provider payloads, or response bodies. The temporary selector and
CaseDetail diagnostics were removed after the matrix; the complete pre-diagnosis diff
identity was restored to `14498c25314e21a131a94e5c98bba63297cfafa4` before this
report append.

The initial restricted attempt failed before browser startup at the known local
Vite/esbuild `spawn EPERM` sandbox boundary. One permitted invocation used an
over-anchored grep and selected no test. Neither is counted below.

### Direct isolated case-detail matrix

| Run | Backend/frontend | URL transition | CaseDetail/query/cache/render result | Final result |
|---|---:|---|---|---|
| 1 | `8910/4320` | exact route completed | mounted; current detail/documents/ownership dispatched and completed `200/200/404-as-null`; all three published independently; `loading -> content`; heading/action visible | PASS |
| 2 | `8911/4321` | exact route completed | same milestones and statuses; heading/action visible | PASS |
| 3 | `8912/4322` | exact route completed | same milestones and statuses; heading/action visible | PASS |
| 4 | `8913/4323` | exact pathname transition completed | no CaseDetail mount, case GET dispatch, QueryClient publication, render-state, or expected-content milestone before the existing assertion failed | FAIL |
| 5 | `8915/4325` | exact route returned HTTP `200` | mounted; current detail/documents/ownership dispatched and completed `200/200/404-as-null`; all three published independently; `loading -> content`; heading/action visible | PASS |

In each passing development-mode run, React StrictMode performed one intentional
mount/unmount cycle. Its first exact detail/documents/ownership requests were aborted,
then the remounted current generation dispatched fresh requests that completed and
published successfully. This is an observed normal path in the passing runs; it does
not establish the mechanism of run 4.

### Deepest milestone and classification

Direct acceptance result: **4/5**, not the required **5/5**.

For run 4, navigation was dispatched and the expected pathname transition completed.
No `CaseDetail` mount was observed afterward, so detail/documents/ownership query
dispatch, response completion, QueryClient publication, and component loading/error/
content render states were not reached or observed. The exact failure class is:

`ROUTE_CHANGED_COMPONENT_NOT_MOUNTED`

The causal/root status remains `DEEPEST_CONFIRMED_ROOT_UNKNOWN`. The evidence does not
prove an auth-state, router, Vite/resource, React bootstrap, or test-synchronization
owner, and the next bounded reproduction after extra resource/page-error observation
passed without such an event. No timeout, sleep, reload, retry, router change, query
change, or product fix is justified by this evidence.

### Stop decision after direct diagnosis

The assignment requires direct case-detail acceptance of `5/5`. Because this matrix is
`4/5` and the owner remains unknown, the mandatory stop rule applies. The responsive
matrix was not restarted; the document-review `3/3` matrix, neighboring selectors,
complete E2E suites, Windows lifecycle, broad final verification, independent quality
gate, commit, push, PR update, and fresh CI were not reached.

No ACRA, Garden Business, BizFile, provider, business-rule, API/model/type, persistence,
schema, mapping, authorization, architecture, or Phase 22 behavior changed. The next
bounded action is to instrument the application bootstrap/AuthProvider/WorkspaceRoutes
boundary before navigation and retain resource/page-error milestones through a
reproduced failure, without increasing the assertion timeout or retrying the flow.

## Application Bootstrap / Auth / Route Commit Diagnosis

Date: 2026-09-23

### Capability and candidate boundary

The task began at committed and published HEAD
`5ad738af2a07c6fc28ed379104079abeb2fa91a3` on
`integration/acra-teammate-reconciliation`, with fetched `origin/main` still
`ef338c9b7926a298e8987acb975fd93c96ed2bfb`. The working tree contained exactly the
12 assigned task-owned dirty paths. Python 3.12.10, Node 22.23.2, npm 10.9.8, and the
repository-pinned local Playwright/Vite dependencies were available. Browser/process
evidence required permitted execution outside the restricted process sandbox; every
execution used distinct loopback ports and task-owned process cleanup. Mongo and
external providers were not relevant.

### Browser-error-first diagnostic

A temporary exact selector exercised:

`Maya login -> low-confidence intake -> WAITING_FOR_REVIEW -> logout -> Ethan login -> direct page.goto(case detail) -> review heading/action visible`

Before application-source instrumentation, it recorded sanitized `pageerror`,
error-level console, failed-request, `401`/`403`/`5xx`, pathname, and fixed visible-state
categories. Five isolated executions on `8920/4330` through `8924/4334` all passed.
Immediately after each direct document navigation, the pathname was
`/cases/{case_id}` and the expected transient view was `Restoring session…`; the Main
workspace had not yet committed. Each run then rendered the review heading and action.
There was no page error, module/resource failure, sign-in replacement, unavailable
route, error fallback, or `401`/`403`/`5xx` after the direct navigation. Failed requests
were navigation/StrictMode cancellation evidence. The case ownership request produced
the existing expected `404-as-null` console response.

The only observed `401` responses and `HTTP_401_CALLBACK` clear occurred during the
deliberate anonymous `/` load before Ethan signed in. They did not occur around direct
case navigation and did not clear the restored authenticated session.

### Auth and route owner-chain trace

The temporary diagnostic was extended under `VITE_E2E_DIAGNOSTICS=1` across the exact
owner chain. Five further isolated executions on `8930/4340` through `8934/4344` all
passed with this direct-navigation order:

1. `AUTH_SESSION_RESTORE_STARTED` and the expected committed loading view;
2. `AUTH_SESSION_RESTORE_SUCCEEDED`, `AUTH_ACCEPT_SESSION`, and
   `AUTH_STATE_AUTHENTICATED`;
3. `AUTHENTICATED_APPLICATION_APP` and its committed effect;
4. `APP_RENDER`, `WORKSPACE_ROUTES_RENDER`, then `CASE_ROUTE_MATCHED`;
5. `CASE_PARAM_ROUTE_RENDER` and `CASE_PARAM_ACCEPTED` for the exact 36-character UUID;
6. `CASE_DETAIL_RENDER_INVOKED` and `CASE_DETAIL_MOUNTED`;
7. `APP_COMMIT` with `/cases/{case_id}`, required capability `CASE_ACCESS`, and the
   capability present;
8. expected review heading and action visible.

React StrictMode produced the expected duplicate render/effect milestones and aborted
the first-generation detail/documents/ownership/profile requests before the remounted
generation completed. It did not clear the authenticated session, reject the route,
invalidate the UUID, or prevent the CaseDetail commit. No source fix was justified.

### Direct case-detail acceptance matrix

| Run | Backend/frontend | Auth after navigation | Last committed bootstrap milestone | Route/parameter | Page/resource error | Final |
|---|---:|---|---|---|---|---|
| 1 | `8930/4340` | restored authenticated | `CASE_DETAIL_MOUNTED` / `APP_COMMIT` | matched / accepted | none unexpected | PASS |
| 2 | `8931/4341` | restored authenticated | `CASE_DETAIL_MOUNTED` / `APP_COMMIT` | matched / accepted | none unexpected | PASS |
| 3 | `8932/4342` | restored authenticated | `CASE_DETAIL_MOUNTED` / `APP_COMMIT` | matched / accepted | none unexpected | PASS |
| 4 | `8933/4343` | restored authenticated | `CASE_DETAIL_MOUNTED` / `APP_COMMIT` | matched / accepted | none unexpected | PASS |
| 5 | `8934/4344` | restored authenticated | `CASE_DETAIL_MOUNTED` / `APP_COMMIT` | matched / accepted | none unexpected | PASS |

Direct acceptance is **5/5**. The earlier `ROUTE_CHANGED_COMPONENT_NOT_MOUNTED` event is
therefore `TRANSIENT_NON_REPRODUCED` in this bounded sample. No hidden page, resource,
auth, capability, route-match, UUID-validation, StrictMode-lifecycle, or component-
commit error was observed. This does not identify a latent recurrence generator and is
not a claim that one cannot exist.

The temporary selector and all bootstrap/auth/route/CaseDetail instrumentation were
removed. TypeScript passed after removal, and Git content identities confirmed the
temporary-only `main.tsx`, `auth.tsx`, `navigation.tsx`, and `App.tsx` edits were fully
restored. The working tree returned to the original 12 assigned paths.

### Restarted responsive matrix and new stop

The exact responsive selector was restarted on the restored candidate. The unchanged
15-second assertions and no-retry behavior were preserved.

| Run | Backend/frontend | Result | Deepest evidence |
|---|---:|---|---|
| 1 | `8940/4350` | PASS | complete responsive selector, including review heading/action |
| 2 | `8941/4351` | PASS | complete responsive selector, including review heading/action |
| 3 | `8942/4352` | FAIL | `Document evidence and review` heading visible; first `Accept … suggestion` action absent at the unchanged 15-second assertion |
| 4 | not run | STOPPED | responsive acceptance had already failed |
| 5 | not run | STOPPED | responsive acceptance had already failed |

This failure is not the earlier route-without-mount boundary: the CaseDetail document-
evidence heading committed. The exact classification is
`DOCUMENT_REVIEW_HEADING_VISIBLE_ACTION_NOT_RENDERED`; the causal/root status is
`DEEPEST_CONFIRMED_ROOT_UNKNOWN`. This execution had no retained application trace
proving whether the current document query was loading, empty, stale, errored, or
published without an actionable pending field, so no source or test-synchronization
fix is justified.

### Mandatory stop

The responsive matrix is not `5/5`; the assignment's stop rule applies. The remaining
responsive runs, document-review `3/3`, neighboring selectors, two complete E2E suites,
Windows lifecycle, broad final verification, independent QG, commit, push, PR update,
and fresh CI were not run. No ACRA, Garden Business, BizFile, provider, backend
workflow, business-rule, API/model/type, persistence, schema, mapping, authorization,
architecture, or Phase 22 behavior was changed.

The next bounded diagnostic owner is the CaseDetail document-query-to-
`DocumentEvidencePanel` render path for the responsive run-3 failure. It must distinguish
query dispatch/completion/publication, selected current document, pending-field action
derivation, and rendered state without increasing timeouts, sleeping, reloading,
retrying navigation, or weakening the selector.

## Self-Review

The final diff was challenged against the original dual-CI failure and all requested adverse cases. The release proof is positive, exact-port, bounded, fail-closed, and socket-closing. The strict preflight remains. No fixed-sleep-only repair, reuse-option bypass, broad process kill, or product-facing delta is present. The original failure class is prevented at its canonical lifecycle owner.

## Document Review Action Render Diagnosis

### Scope and evidence boundary

This continuation inspected the exact `DocumentEvidencePanel` action predicates and
traced the failing responsive scenario through the authoritative documents response,
the actor/case-scoped React Query result, and the rendered panel. Diagnostics retained
only opaque IDs, state/status enums, field keys, counts, comparison/review statuses,
suggestion-presence booleans, action-eligibility booleans, and case stage/status. No
document value, canonical/reviewed value, note, body, credential, session value, or
sensitive filename was logged.

The temporary query/render instrumentation was removed after diagnosis. The retained
change is test-only: the browser test now registers for the exact authoritative
documents GET before direct case navigation, verifies that the current document is
`REVIEW_REQUIRED` with at least one `PENDING` field that has a suggestion, and then
performs the unchanged visible Accept-action assertion. A focused browser regression
uses the same public HTTP and rendered-action boundary. There is no sleep, reload,
re-navigation, retry, timeout increase, or weakened action assertion.

### Three truth layers and false predicate

| Layer | Safe observed projection | Result |
|---|---|---|
| Backend authoritative documents GET | one current document; `state=REVIEW_REQUIRED`; `field_count=4`; `pending_count=4`; `final_count=0`; every field `review_status=PENDING`; every field had an original suggestion | Correct |
| React Query document state | before completion: `status=pending`, `fetch_status=fetching`, `document_count=0`; after completion: the same one-current/four-pending projection as the backend | Correct after authoritative load |
| Rendered panel | before completion: heading rendered with `documents=[]`; after completion: every field had `canDecide=true` and `acceptVisible=true` | Correct after authoritative load |

The exact false action-render predicate at the premature rendered state was the absence
of a selected current document: `documents=[]`, so no field reached the
`historical == false && isCurrentDocument(document) && state == REVIEW_REQUIRED &&
review_status == PENDING` decision block. `busy=false` and `mutationBlocked=false`; they
did not hide the block. Once authoritative data arrived, `state`, `review_status`, and
`has_original_extracted_value` were all valid and the Accept action rendered.

Classification: **`TEST_ASSERTS_BEFORE_AUTHORITATIVE_DOCUMENT_LOAD`**.

No evidence supported `BACKEND_DOCUMENT_NOT_REVIEW_REQUIRED`,
`BACKEND_FIELD_NOT_PENDING`, `BACKEND_FIELD_MISSING_SUGGESTION`,
`QUERY_DOCUMENT_STALE`, `QUERY_DOCUMENT_WRONG_IDENTITY`,
`QUERY_CURRENT_DOCUMENT_SELECTION_STALE`, `RENDER_CANDECIDE_FALSE_DESPITE_VALID_QUERY`,
`RENDER_ORIGINAL_VALUE_FALSE_DESPITE_VALID_QUERY`, or
`MUTATION_BLOCKED_DISABLED_ONLY` for this boundary.

### Direct review-ready matrix

The focused selector
`review-ready actions render after authoritative current document evidence loads` was
run in five fresh guarded lifecycles. Each run created the same low-confidence review
case, waited for `WAITING_FOR_REVIEW`, registered for the exact browser documents GET,
verified the safe backend projection above, and observed the unchanged Accept action.

| Run | Backend/frontend | Backend | Query/render | Action | Result |
|---|---:|---|---|---|---|
| 1 | `8960/4370` | `REVIEW_REQUIRED`, 4 pending, suggestions present | authoritative response consumed; panel action visible | visible | PASS |
| 2 | `8961/4371` | same | same | visible | PASS |
| 3 | `8962/4372` | same | same | visible | PASS |
| 4 | `8963/4373` | same | same | visible | PASS |
| 5 | `8964/4374` | same | same | visible | PASS |

Direct review-ready acceptance: **5/5 PASS**. No retry occurred inside any lifecycle.

### Responsive restart and repeated unrelated stop

Before the final restart, diagnostic responsive executions produced two unrelated
failures outside the document-action boundary:

- `8952/4362`: the first clean-case upload completed through browser, Vite, backend,
  and HTTP `201`, but `/new-onboarding/{case_id}` did not appear within the unchanged
  route assertion;
- `8953/4363`: both cases were created and the review document projection became
  actionable, but the selector later timed out waiting for the completed-case link on
  the Onboarded screen.

After the document-readiness fix and direct 5/5 evidence, the exact responsive matrix
was restarted from run 1 without diagnostics:

| Run | Backend/frontend | Result | Deepest evidence |
|---|---:|---|---|
| 1 | `8970/4380` | FAIL | `/new-onboarding/{case_id}` did not appear after the first case creation within the unchanged 30-second route assertion |
| 2–5 | not run | STOPPED | the post-upload route failure had now repeated |

The run-1 symptom matches the earlier `8952/4362` post-upload route failure. Its deepest
confirmed root remains unknown; it is outside the proved document-readiness mechanism.
Per the assignment's repeated-product-failure and responsive `5/5` stop rules, execution
stopped immediately. The authenticated document-review `3/3`, neighboring selectors,
two full E2E passes, broad verification, independent QG, commit, push, and fresh CI were
not reached.

### Focused verification and stop receipt

- `npm.cmd run typecheck`: PASS.
- `npm.cmd test -- --run src/pages/DocumentEvidencePanel.test.tsx src/Phase15CNavigation.test.tsx`:
  **51/51 PASS** across 2 files.
- direct review-ready guarded browser matrix: **5/5 PASS**.
- responsive matrix after the fix: **0/1 PASS; STOPPED on run 1**.
- document-review matrix: **not reached**.
- full E2E twice: **not reached**.
- independent QG: **not started**.
- commit/push/CI: **not performed**.

The working candidate remains the same task-owned 12-path inventory. No ACRA, Garden
Business, BizFile, provider, backend workflow, API/model/type, persistence, schema,
mapping, authorization/security, business-rule, architecture, or Phase 22 behavior was
changed by this diagnosis. The new test-only delta is confined to the two already-owned
frontend E2E files plus this chronological report update.

## Retained Intake Route Transition Diagnosis

### Guard authority and diagnostic method

Phase 15C introduced the exact-path guard deliberately: a late case-create response may
move to `/new-onboarding/{case_id}` only while the user remains at the originating fresh
onboarding destination. If the user has left, stale completion must not steal the newer
route. The guard therefore cannot be removed merely to mask the intermittent symptom.

Temporary diagnostics under the existing explicit E2E diagnostic mode recorded only
monotonic browser time, sanitized pathname, milestone, and opaque case UUID. They
covered `START_NEW_CASE_CLICK`, `START_NEW_CASE_NAVIGATE_REQUESTED`, path before reset,
router commit, Create click/request/response, `onCreated` pathname/case identity, guard
decision, and final pathname. No document value/body, filename, credential, token,
cookie, CSRF value, provider payload, or private error detail was emitted. The temporary
App instrumentation and temporary selector were removed after the bounded matrix.

Each isolated sequence performed: create case A; retain its intake binding; select New
onboarding; click Start a new case; observe the pathname immediately; create case B;
observe the `onCreated` guard and final case-B route. Times below are per-page monotonic
milliseconds and are comparable only within a row.

| Run | Ports | Exact old retained path | Start click / navigate requested | Fresh pathname first observed / commit effect | Second Create click / request | Create response / `onCreated` path | Guard decision | Final pathname |
|---|---:|---|---:|---:|---:|---|---|---|
| 1 | `8980/4390` | `/new-onboarding/01cabf2c-c347-46df-ac3b-98d0fbf2f5b7` | `832 / 833` | `842 / 848` | `898 / 898` | `931 / /new-onboarding` | retained navigation requested | `/new-onboarding/60d46286-b858-4609-9da5-9c0e6870e180` |
| 2 | `8981/4391` | `/new-onboarding/5917d84a-88e4-451c-9221-ea2785e44e81` | `860 / 860` | `869 / 877` | `1026 / 1026` | `1050 / /new-onboarding` | retained navigation requested | `/new-onboarding/56eb85f4-693f-4d6a-89aa-5abf9e10d0f4` |
| 3 | `8982/4392` | `/new-onboarding/fdbe38b5-257b-400b-abb8-4667abf94ca5` | `855 / 856` | `865 / 872` | `1022 / 1022` | `1052 / /new-onboarding` | retained navigation requested | `/new-onboarding/ee995cdd-3d1f-4a41-8f6f-b37ea10fd128` |
| 4 | `8983/4393` | `/new-onboarding/d7b5596b-d2ca-4c60-9138-95cd15bb02a9` | `793 / 793` | `802 / 808` | `959 / 959` | `988 / /new-onboarding` | retained navigation requested | `/new-onboarding/9293a195-8840-41fe-bd9b-54b580933506` |
| 5 | `8984/4394` | `/new-onboarding/9b6978a5-546e-40da-9659-7e1b26e7d98a` | `758 / 758` | `767 / 774` | `941 / 941` | `982 / /new-onboarding` | retained navigation requested | `/new-onboarding/a8ac3959-cbe1-4d46-aa2f-2b6891187a95` |

Direct transition result: **5/5 PASS**. In every run the browser pathname was already
exactly `/new-onboarding` immediately after the Start-a-new-case click completed. The
router commit effect followed 14-17 ms after the navigation request, while the next
Create action occurred 50-167 ms after that commit effect. Every create response then
entered `onCreated` with `/new-onboarding`; the exact-path guard was true, retained
navigation executed, and the prior retained case ID never became the new route identity.

### Classification and stop decision

The only directly proved timing label is **`ROUTER_COMMIT_DELAY_ONLY`**: a small
request-to-commit interval exists, but it completed before the form was submitted in all
five isolated sequences. `TEST_STARTS_CREATE_BEFORE_FRESH_ROUTE_COMMIT`,
`ONCREATED_PATH_GUARD_RACE`, `RETAINED_INTAKE_BINDING_STALE`,
`WORKSPACE_TAB_TARGET_STALE`, and `CREATE_RESPONSE_BEATS_ROUTE_COMMIT` were not observed.
The guard was never false.

No TEST-ONLY race was proved, because the current Playwright sequence did not submit
before route commitment. No PRODUCT RACE was proved, because the real rendered form was
not used to create case B before the fresh route committed in any run. The earlier
responsive route failure remains **`DEEPEST_CONFIRMED_ROOT_UNKNOWN`**. The falsifier for
the proposed race was a second Create or `onCreated` event preceding the fresh route
commit, or an `ON_CREATED_RETAINED_NAV_SKIPPED` decision; none occurred.

Change Necessity: the proposed cause was not established, a no-change diagnostic stop
preserves the Phase 15C stale-navigation invariant, and the assignment explicitly bars
implementation when the hypothesis is disproved while root ownership remains unknown.
Decision: **no-change**. No wait, sleep, retry, timeout increase, guard removal, product
change, or test-synchronization change was retained.

Per the mandatory stop rule, the responsive `5/5`, document-review `3/3`, two complete
E2E passes, broad final verification, independent QG, commit, push, PR mutation, and
fresh push/PR CI were not run. No Phase 22 work was started.

## Responsive E2E Decomposition

### Investigation boundary and task-start identity

The bounded follow-up tested whether the single long responsive Playwright scenario was
coupling otherwise independent workflows inside one browser lifecycle. The repository
started on `integration/acra-teammate-reconciliation` at published HEAD
`5ad738af2a07c6fc28ed379104079abeb2fa91a3`; a fresh fetch confirmed `origin/main` and
the merge base remained `ef338c9b7926a298e8987acb975fd93c96ed2bfb`, with the feature
branch four commits ahead and zero behind. The working tree contained exactly the 12
assigned task-owned paths listed in the handoff. Python 3.12.10, Node 22.23.2, npm
10.9.8, and repository-pinned Playwright 1.56.1 were available. Mongo and external
providers were not relevant. Browser runs used deterministic distinct loopback port
pairs and the existing task-owned process cleanup.

After the stop, the exact binary Git diff across the 11 non-report task-owned paths had
SHA-256 `14b8a7c6c2be7d92700dda0d8ab7c6eba464bbcf17b6c13316e8727de8b9fd4d`.
Together with this report, the dirty inventory remained exactly the assigned 12 paths.

The old responsive test combined anonymous layout, seven viewport widths, primary
navigation, account hover/focus, two case creations and status polling, representative
case/onboarded/audit/policy routes, table alignment and local scrolling, role-based
policy controls, review readiness, a delete dialog, three role changes, logout, and HR
administration in one browser lifecycle.

### Independent selector boundaries

`responsive-layout.e2e.ts` now discovers six independently executable selectors:

1. responsive shell: anonymous auth card, all seven viewport widths, Dashboard, New
   onboarding, shell/nav/form containment, account hover, keyboard focus, and logout;
2. cases and representative routes: its own clean and low-confidence cases, real
   upload/status progression, Dashboard, New onboarding, Cases, review case detail,
   Onboarded, onboarded detail, Audit, Policy, local table scrolling, Cases column
   alignment, priority labels, and Client Onboarder policy restrictions;
3. review case controls: its own low-confidence case, authoritative current-document
   response, visible Accept suggestion, absent unsupported reviewer/rework controls,
   and document containment;
4. Relationship Manager controls: independent Ethan login, its own clean case, policy
   mutation controls, and contained delete/cancel dialog;
5. Director policy: independent Olivia login, contained shell, and policy mutation
   controls;
6. HR administration: independent HR login, Users/Teams/Policy at 360/768/1440 px,
   contained shell, and absent policy mutation controls.

No mutable case ID crosses a selector. Each case-owning selector creates its required
state through the existing real browser workflow. Shared helpers only centralize the
unchanged policy-control and authoritative-review assertions. There are no Playwright
retries, reload recovery, arbitrary waits, duplicate navigation/POST recovery, skips,
catch-and-continue assertions, or product changes. The original 240-second test timeout
was retained only on selectors that exercise the same bounded workflow/status work; no
assertion timeout was increased.

### Assertion-preservation map

| Prior coverage | Decomposed owner |
|---|---|
| auth-card/root containment, seven viewport widths, shell/nav/environment/account containment, responsive form, hover/focus, logout | responsive shell |
| real clean/review creation, upload, status progression, representative routes, local scrollers, Cases 12-column alignment, Unset/Low/Medium/High, Client Onboarder policy restrictions | cases and representative routes |
| authoritative `REVIEW_REQUIRED` current document, pending suggestion, visible Accept action, unsupported Assign/Return absent, root containment | review case controls |
| Relationship Manager policy controls, real owned case, responsive delete dialog and Cancel containment | Relationship Manager controls |
| Director policy mutation visibility | Director policy |
| HR Users/Teams/Policy responsive widths and policy-mutation absence | HR administration |

TypeScript passed after decomposition. Playwright discovery changed from eight configured
tests to 13: the original responsive selector became six selectors while the seven
authenticated selectors remained present. Static inspection found no prohibited
flakiness-masking construct.

### Repeated isolated evidence

Each invocation below used `python scripts/run_e2e.py --grep <unique title>` with a
fresh backend/frontend/browser lifecycle and distinct deterministic ports.

| Selector | Initial three-run pattern | Additional bounded evidence |
|---|---|---|
| responsive shell | PASS / PASS / PASS (`9111/4521` through `9113/4523`) | none required |
| cases and representative routes | PASS / PASS / FAIL (`9121/4531` through `9123/4533`) | unchanged repeat PASS / PASS / PASS (`9124/4534` through `9126/4536`); responsive-sequence attempt then FAIL at `9172/4582` |
| review case controls | PASS / PASS / PASS (`9131/4541` through `9133/4543`) | none required |
| Relationship Manager controls | PASS / PASS / PASS (`9141/4551` through `9143/4553`) | none required |
| Director policy | PASS / PASS / PASS (`9151/4561` through `9153/4563`) | none required |
| HR administration | PASS / PASS / PASS (`9161/4571` through `9163/4573`) | none required |

The first cases/routes failure occurred after the first real case upload: the expected
`/new-onboarding/{case_id}` route did not appear within the unchanged 30-second route
assertion. The later unchanged repeat supplied a clean three-run sample, so the first
complete responsive-file sequence began. Its shell selector passed. The cases/routes
selector then failed a second time while creating its own second (review) case: the
real `Create onboarding` click never completed before the retained 240-second test
deadline. No later selector in that sequence ran.

### Stop classification

The same independently bounded cases/routes selector has now failed twice, at two case-
creation boundaries. This triggers the explicit stop rule. The exact smaller blocker is
the **responsive cases and representative routes selector's two-case creation
workflow**. The deepest confirmed root remains unknown; current evidence does not prove
a product owner, browser/runtime mechanism, upload owner, route owner, or a single common
mechanism for the two manifestations. The causal topology therefore remains unknown.

Decomposition is **not** supported as having solved the instability, and this report
does not classify the primary issue as monolithic or long-lived scenario coupling. It
does show that the instability survives after unrelated role/admin/review workflows are
removed from the failing selector.

Responsive-file sequence result: first attempt **1/6 PASS, then STOPPED on the second
selector**; a second responsive-file sequence was not run. Authenticated document review
`3/3`, full configured E2E twice, broad final verification, Windows lifecycle,
independent QG, commit, push, PR update, and fresh CI were not reached. No ACRA, Garden
Business, BizFile, ownership/UBO, GoldTier, Mongo, priority/policy semantics, provider
readiness, API/model/type, persistence/schema, authorization/security, architecture, or
Phase 22 behavior changed.

## Cases / Representative Routes Workload Isolation

### Coverage audit and final boundary

The stopped cases/routes selector created both a clean completed case and a
low-confidence review case. The second case was not necessary for its route/layout
responsibilities:

- Dashboard, New onboarding, Cases, Audit, Policy, local scrollers, the Cases
  12-column alignment checks, priority labels, and Client Onboarder policy restrictions
  do not depend on review state.
- `/cases/{id}` renders the required Document evidence and review heading for the
  completed case, while `/onboarded/{id}` specifically requires that completed case.
- Review-specific `REVIEW_REQUIRED` state, the pending suggestion, visible Accept
  control, and absence of unsupported Assign/Return controls remain owned by the
  independent responsive review selector.

The representative-routes selector therefore now creates exactly one clean case, waits
for `COMPLETED`, and uses that same case ID for both detail routes. This removes the
redundant low-confidence case without deleting an assertion or weakening a product
contract.

The existing product invariant for starting a new onboarding while an earlier case is
retained still needed browser coverage. It is now isolated in the focused selector
`starting a fresh onboarding after a retained case binds the new case route`. That
selector creates case A through the real form/upload workflow, explicitly chooses
Start a new case, proves the exact fresh `/new-onboarding` route, creates case B through
the same real workflow, proves the new UUID route, and proves the two IDs differ. The
responsive file consequently discovers seven independent selectors and the complete
configured suite discovers 14 tests. No product source, retry, reload, arbitrary sleep,
skip, timeout increase, or assertion weakening was introduced by this final isolation.

### Bounded repeated evidence

Every focused browser invocation used `python scripts/run_e2e.py --grep <title>` with
its own backend, frontend, browser, deterministic fresh port pair, and task-owned
cleanup.

- The one-case cases/routes selector first produced **PASS / FAIL / PASS / PASS /
  PASS** on `9201/4601` through `9205/4605`. In run 2 the browser had reached
  `/dashboard`, but the unchanged 15-second Dashboard-heading assertion did not render.
  Two bounded continuations on `9206/4606` and `9207/4607` both passed, yielding the
  required **five consecutive passes in runs 3-7**. The isolated Dashboard miss did not
  recur and its lower mechanism remains unknown.
- The focused retained-case/new-case route selector passed **5/5** on `9221/4621`
  through `9225/4625`.
- Each of the seven responsive selectors then passed three fresh isolated repetitions:
  **21/21**, using `9241/4641` through `9261/4661`.
- Two further complete responsive-file sequences passed **7/7** and **7/7**, using
  `9301/4701` through `9314/4714`.
- The authenticated document-review selector passed **3/3** with diagnostics on
  `9341/4741` through `9343/4743`. Each run observed the real upload `201`, then the
  unchanged progression through one, two, three, and four final fields; there was no
  duplicate mutation dispatch.
- Two unchanged complete configured E2E suites each passed **14/14** with independently
  isolated selector lifecycles.

The supported classification is **`MULTI_CASE_RESPONSIVE_TEST_COUPLING`** at the test
workload/ownership level: the representative-routes selector unnecessarily paid for a
second case whose review assertions already had an independent owner, and the retained
two-case behavior remains green when exercised at its narrow boundary. This is not a
claim that the earlier low-level browser/runtime symptom was identified. In particular,
the single-case matrix contained one non-repeating Dashboard-render miss before the
five-consecutive-pass window. The evidence supports workload isolation as the smallest
sufficient test-design correction; the deepest mechanism for the historical individual
timeouts remains unknown.

### Final verification on the exact candidate

- Runner unit suite: **32 passed**.
- Focused backend document API suite: **22 passed**.
- Focused frontend navigation/review suites: **51 passed**.
- Full frontend suite: **20 files, 274 tests passed**.
- Full backend suite: **1129 passed, 28 skipped**, with four pre-existing warnings.
- Windows lifecycle suite: **23 passed**.
- Full configured E2E: **14/14 PASS twice**.
- Frontend typecheck and production build: **PASS**; build processed 112 modules.
- Ruff across `apps/backend`, `scripts`, and `tests`: **PASS**.
- `npm ls --all`: **PASS**, with only expected unmet optional cross-platform packages.
- Project-state, architecture, tooling-configuration, and secret checks: **PASS**.
- `git diff --check`: **PASS** apart from informational line-ending notices.

The final change preserves the existing ACRA/IDP/ownership/GoldTier/Mongo capability
classifications and changes no API/model/type, persistence/schema, connector,
configuration, mapping, business rule, authorization/security, provider status, or
architecture boundary. No Phase 22 work was started. The exact dirty candidate is now
eligible for the required fresh independent quality gate; commit and publication remain
conditional on an exact `PASS`. The frozen SHA-256 of the binary Git diff across the 11
non-report task-owned paths is
`3a8898f4d5b6eb199e22d8df74717d1c77f466a645a96120e0d935b1c093c6ad`.

## Independent-QG Portfolio Reload Failure Diagnosis

### QG failure identity and bounded scope

The fresh independent gate at
`.ai-pipeline/reports/PR52_E2E_PORT_RELEASE_REMEDIATION_QUALITY_GATE.md`
remains an immutable **FAIL**. Its only blocker was selector 2/14,
`Singapore clean fixture completes the truthful Mock target path`, timing out at the
first post-`page.reload()` `waitForResponse` for
`GET /api/clm/zero-touch/case-portfolio`. The gate's one immediate isolated rerun
passed. This investigation did not revisit responsive decomposition, upload transport,
port isolation, review-cache behavior, ACRA, Garden Business, or BizFile.

The executable non-report candidate was restored after diagnostics to the exact prior
binary-diff SHA-256
`3a8898f4d5b6eb199e22d8df74717d1c77f466a645a96120e0d935b1c093c6ad`.
No product, auth, query, API, runner, browser-test, timeout, retry, polling, provider,
persistence, schema, business-rule, mapping, authorization, or architecture behavior
was changed by this investigation.

### Safe diagnostic method

Temporary instrumentation was attached only around the two reloads in the exact
selector. It observed browser `request`, `response`, `requestfailed`, `pageerror`, and
error-console events and recorded only monotonic elapsed time, sanitized route family,
method, status, coarse failure category, page pathname, and a finite visible app-state
enum. It recorded no credentials, cookies, CSRF values, headers, response bodies, case
contents, legal names, documents, or provider payloads. An independent response-event
observer ran beside the unchanged `waitForResponse` owner.

The trace was then applied to a temporary reload-only selector:

`login -> initial default portfolio response -> Cases -> reload -> restored portfolio
response -> Cases render`

The temporary selector and all reload-trace source were removed after diagnosis. Six
initial matrix attempts were rejected before browser startup because the restricted
sandbox denied Vite/esbuild process creation with `spawn EPERM`; the permitted rerun
provided the actual browser evidence below. A later 20-run reload-only invocation from
the wrong working directory also exited with code 2 before startup and is not counted
as runtime evidence.

### Auth, view, and request-chain observations

Every traced successful reload followed the same sequence:

1. `/cases` document `GET` returned `200`.
2. `AuthenticatedApplication` visibly entered `Restoring session...`.
3. React development StrictMode dispatched two `GET /api/auth/me` requests; both
   returned `200` in the representative configured-suite trace.
4. Authenticated transport was restored and the default portfolio query began.
5. Two browser portfolio requests were observed 4-9 ms apart.
6. The first request emitted `requestfailed` with the coarse `ABORTED` category.
7. The replacement request returned `200` through the same-origin Vite proxy.
8. The independent response observer saw the response and the pre-armed
   `waitForResponse` resolved.
9. The exact Cases heading rendered; Login and Page unavailable did not render, and no
   page error or error-console milestone was observed.

The installed TanStack Query 5.102.8 source explains the observed cancellation:
`Query.removeObserver` cancels an in-flight retryer with `revert: true` when the final
observer is removed and the query function consumed its `AbortSignal`. The current
portfolio query deliberately consumes that signal. React StrictMode's transient
mount/unmount therefore accounts for the first aborted request; the remount normally
starts the successful replacement. This is a confirmed normal-path mechanism, not proof
that the historical QG occurrence failed for that reason.

No successful trace required deeper Vite/backend portfolio instrumentation: a browser
`200` response from the same-origin proxied route proves that Vite accepted and completed
the upstream exchange and that the backend route completed. There was no observed
browser-dispatched/no-completion occurrence to distinguish further at those layers.

### Exact clean-fixture diagnostic matrix

Each run used a fresh isolated backend/frontend/browser lifecycle, one unique port pair,
no within-run retry, and the unchanged selector success conditions.

| Run | Backend/frontend | Result | Auth restore | Portfolio browser chain | Observer / waiter | Cases |
|---:|---:|---|---|---|---|---|
| 1 | `9501/4901` | PASS | restored | abort then `200` | YES / YES | committed |
| 2 | `9502/4902` | PASS | restored | abort then `200` | YES / YES | committed |
| 3 | `9503/4903` | PASS | restored | abort then `200` | YES / YES | committed |
| 4 | `9504/4904` | PASS | restored | abort then `200` | YES / YES | committed |
| 5 | `9505/4905` | PASS | restored | abort then `200` | YES / YES | committed |
| 6 | `9506/4906` | PASS | restored | abort then `200` | YES / YES | committed |
| 7 | `9507/4907` | PASS | restored | abort then `200` | YES / YES | committed |
| 8 | `9508/4908` | PASS | restored | abort then `200` | YES / YES | committed |
| 9 | `9509/4909` | PASS | restored | abort then `200` | YES / YES | committed |
| 10 | `9510/4910` | PASS | restored | abort then `200` | YES / YES | committed |

Observed reload-request elapsed windows across these runs were bounded: portfolio
dispatch began roughly 166-185 ms after arming, the successful `200` arrived roughly
221-256 ms after arming, and Cases was confirmed committed roughly 263-333 ms after
arming in the corresponding reload-only sample. No timeout increase was used.

### Reload-only focused evidence

After correcting a diagnostic-only exact-heading locator that initially matched
Dashboard headings containing the word "cases", the valid reload-only matrix produced:

- runs 1-19 on `9641/5041` through `9659/5059`: **19/19 PASS** with the same
  abort-then-`200`, observer/waiter YES/YES, Cases-committed chain;
- run 20 on `9660/5060`: **FAIL before `RELOAD_ARMED`**, with no reload trace emitted;
  because the filtered matrix retained only selected lines, its exact earlier assertion
  was not available and it supplies no evidence about the QG post-reload boundary;
- a detail-preserving repeat on `9671/5071` through `9680/5080`: **10/10 PASS** with
  the same reload chain. One run additionally observed an obsolete StrictMode auth read
  abort while the current auth read still returned `200`; the portfolio replacement
  completed and Cases committed.

The configured pre-correction command `python scripts/run_e2e.py` also passed **14/14**
with the exact selector at lifecycle 2/14 and the full traced chain above. This is
diagnostic evidence only, not the assignment's required post-fix two-run acceptance
because no justified fix exists.

### Classification and stop decision

The evidence rejects these classifications for every observed reload:

- `AUTH_RESTORE_NOT_DISPATCHED`;
- `AUTH_RESTORE_HUNG`;
- `AUTH_RESTORE_FAILED_ANONYMOUS`;
- `CASES_ROUTE_NOT_COMMITTED`;
- `PORTFOLIO_PREFETCH_NOT_DISPATCHED`;
- `PORTFOLIO_VITE_UPSTREAM_HUNG`;
- `PORTFOLIO_BACKEND_HUNG`;
- `PORTFOLIO_RESPONSE_RECEIVED_LISTENER_MISSED`;
- `AUTHENTICATED_CASES_VIEW_NEVER_COMMITTED`.

The observed first portfolio request is accurately classified
`PORTFOLIO_REQUEST_ABORTED`, followed by an expected successful current request. The
installed-source and runtime evidence also confirms
`PORTFOLIO_QUERY_DEDUP_EXPECTATION_MISMATCH` as a description of the normal StrictMode
diagnostic shape: prefetch plus the mounted Cases consumer does not produce one
uninterrupted transport request because transient observer removal cancels the
AbortSignal-aware request and the remount restarts it. It does **not** establish that
this expected cancellation/restart caused the historical QG timeout.

The exact historical failure therefore remains
**`DEEPEST_CONFIRMED_ROOT_UNKNOWN`**. Its uninstrumented run cannot distinguish a
missing restart, host/test-time-budget exhaustion, or another unobserved transient.
Changing auth/prefetch ordering, removing session prefetch, ignoring AbortSignal,
replacing `waitForResponse`, adding retry/reload, or increasing a timeout would be a
speculative correction. The independent observer and waiter agreed in every traced
reload, so a listener-ownership test change is specifically unsupported.

Pre-claim result: causal closure is open at the historical abort-to-restart edge; the
falsifier (observer sees a response while the waiter does not) was checked and absent;
the strongest counterargument (the deterministic first abort is itself the root) fails
because every observed abort was followed by a successful replacement; topology remains
unknown; and the uninstrumented historical occurrence prevents a layer-ceiling proof.

### Outcome A — reload boundary stop

No correction, five-run post-fix matrix, two post-fix full E2E runs, fresh re-QG,
commit, fetch-for-publication, push, CI observation, merge, or Phase 22 work was
performed. The dirty inventory remains the pre-existing 13-path candidate plus this
report's diagnosis; the 11 non-report paths exactly match the historical independently
reviewed candidate hash above. The next authorized action, if the owner wishes to
continue, is a new bounded run that captures the same safe browser/auth/query trace in
the actual failing configured execution and preserves full failure output. It must not
assume the normal StrictMode abort is the historical root without observing the missing
replacement or another terminal milestone.
