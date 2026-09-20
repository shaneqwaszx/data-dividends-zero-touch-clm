# Phase 16 Post-Reset Login Diagnosis

Date: 2026-09-21

Status: **DIAGNOSIS INCOMPLETE — INTEGRATION BLOCKED**

## Scope and identities

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`
- Branch: `phase/16-registry-cache-freshness-planning`
- Current source `HEAD`: `d8fc4ecd04459cfa4b39c920e9e67fab707eb039`
- Integrated `origin/main` observed locally: `bc21070fc1f45729e374a5cbe6425d89b8956ab9`
- Accepted Phase 16 head: `92cc8fa9f971a937b7f6696eb06f8675da7e9b05`
- Current diagnostic test-file blob after final local edits:
  `52e3d86bf469c4754566980ad51e196dea7a227f`
- Interpreter:
  `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix\.venv\Scripts\python.exe`
- Python base prefix: `C:\Python312`
- Backend import and site-packages resolve inside this worktree.

The tracked tree and index were clean at task start. No Git operation or Git lock was
active and no collaborating writer was using the checkout. Available resources used
were the worktree-local Python environment, PowerShell/CMD, local loopback lifecycle
ports, and the local Docker engine with the already available `mongo:7` image. No
browser, external provider, ambient Mongo URI, credential discovery, `.env`, or network
service was used. Initial sandboxed Windows process inspection was permission-limited;
the supported approval path was used only for the differentiated physical lifecycle run
and exact task-owned cleanup.

## Historical failure boundary

The full retained traceback from the 20-test lifecycle execution is available in the
prior task record. The failing frames were:

1. `test_reset_restarts_and_clears_process_local_case` called `request()` for the old
   case after reset;
2. `request()` created a new cookie jar and called `opener.open(login_request,
   timeout=3)`;
3. `urllib` reached `HTTPConnection.getresponse()` and
   `HTTPResponse._read_status()`;
4. the socket timed out while waiting for the HTTP status line.

Therefore the exact observed stage was **login response acquisition before response
headers/status**. The login body was not read, login JSON was not parsed, and the target
old-case GET was not dispatched. This was an authentication-path timeout, not evidence
that case deletion failed.

The earlier Phase 13 event occurred in a different test/helper: the live-loopback
`HttpSeedApi` test using an in-process Uvicorn server after seed mutation work. Retained
evidence identifies an HTTP/in-process request boundary and a later isolated pass, but
does not retain enough stack detail to distinguish response-header acquisition from body
read. The two events therefore must not be assigned a shared cause.

## Diagnostic implementation

Only `tests/test_demo_lifecycle_windows.py` changed.

The real authenticated `request()` helper now records one bounded structural diagnostic
per login or target operation. Fields are limited to operation role, stage,
before/after-reset context, header/body/parse completion, HTTP status when available,
an allowlisted exception category, monotonic elapsed milliseconds, and target-dispatch
state. On failure, the current structural observation is attached as an exception note;
the original exception type and propagation remain unchanged.

The helper does not record credentials, password hashes, cookies, CSRF values, response
headers or bodies, case identifiers, URLs, exception messages, process command lines, or
environment values. It adds no login retry and retains the existing three-second request
timeout. The original authenticated identity, new cookie jar per `request()` call,
target GET, and expected post-reset `404` are unchanged.

No production source, authentication policy, launcher, Vite configuration, dependency,
CI, persistence implementation, API/model/type, schema, connector, business rule,
mapping, architecture owner, or provider classification changed.

## Deterministic evidence

The real helper was exercised with controlled transport objects rather than replaced by
a mock helper. Three unittest methods cover:

- successful login followed by the expected target `404`;
- timeout before login headers;
- timeout during login body read;
- malformed login JSON;
- actual denied login via `HTTPError(401)`;
- successful login followed by target response-acquisition timeout;
- no target dispatch after every login failure;
- exact login/target call counts and no hidden retry;
- unchanged exception classes and propagation; and
- sanitized in-memory diagnostics and exception notes.

Final focused result on current content: **3/3 methods PASS** in 3.007 seconds, including
four login-failure subtests. Focused Ruff, Python compilation, and test-file diff check
passed. Test-first evidence initially failed with six `TypeError` errors because the
unmodified helper did not accept the diagnostic context, then passed after the bounded
implementation.

## Physical lifecycle experiments

### Experiment 1 — sandboxed process boundary

The exact selector was invoked once without prewarming. It failed before reset or login:
the initial launcher health check could not complete because Windows process-tree access
was denied in the sandbox. The supported stop script was then approved and reported that
every recorded launcher-owned partial-start process tree was gone. Ports 8000 and 5173
were free and the runtime manifest was absent afterward.

This experiment proves only a platform-permission prerequisite; it is not application or
authentication evidence.

### Experiment 2 — normal Windows process permissions

The second experiment tested the different documented hypothesis that experiment 1 was
entirely a sandbox process-management limitation. It used the same exact selector,
unchanged code behavior, unchanged three-second request timeout, no prewarming, and the
same memory-mode synthetic-auth launcher composition with normal Windows permissions.

Result: **1/1 PASS in 49.159 seconds**. Initial start, case creation/read, reset, fresh
health, new login, target `404`, and owned shutdown completed. Ports 8000 and 5173 were
free and the runtime manifest was absent afterward.

This non-reproduction demonstrates that the instrumented success path remains valid. It
does not identify the historical cause or establish that the intermittent timeout is
fixed. The physical run preceded a later deterministic-test assertion strengthening and
a control-flow-only refactor that prevents duplicate classification of target body-read
errors; current helper behavior after those edits is covered by the final focused tests,
but no unauthorized third physical run was performed.

## Independent physical Mongo evidence

A unique task-owned `mongo:7` container was started with loopback-only port binding, no
host data directory, no shared named volume, and no privileged mode. The URI existed
only in the physical runner process environment and was not printed or persisted.

`scripts/run_physical_mongo_tests.py` result:

- owned suites: **5**;
- collected: **22**;
- passed: **22**;
- failed: **0**;
- errors: **0**;
- skipped: **0**.

The runner used only generated database names accepted by
`scripts/mongo_test_safety.py`, which rejects `clm_poc` and other non-allowlisted names
and verifies database removal. The exact task-owned container was removed, and a final
container query confirmed cleanup.

This is independent persistence evidence. It does not waive the unresolved lifecycle
failure and is not overall integration acceptance.

## Cause classification and next correction

Observed cause altitude: L3 system/runtime boundary. The historical post-reset event is
classified precisely as a login response-header acquisition timeout. The available
evidence does not distinguish authentication-service latency, server scheduling/resource
contention, response transport handling, or another transient runtime condition. The
single real diagnostic run did not reproduce it.

No genuine harness defect, authentication defect, launcher defect, persistence defect,
or timeout-contract defect has been established. Raising the timeout, retrying login,
reducing scrypt cost, reusing a session, adding sleeps, or changing production code would
be speculative and is not proposed.

The smallest justified next action is diagnostic publication after an exact independent
diagnostic PASS, so a future recurrence can establish the precise boundary. Any later
production authentication, launcher, scheduler, or timeout correction requires new High
scope and evidence from a classified recurrence or separately authorized measurement.

## Conclusion

**DIAGNOSIS INCOMPLETE — INTEGRATION BLOCKED**

Safe stage observability is implemented and locally verified. The historical target GET
did not execute. The permitted real diagnostic did not reproduce the timeout. Physical
Mongo evidence passed independently and cleanup was verified. No causal fix or final
integration acceptance is claimed.
