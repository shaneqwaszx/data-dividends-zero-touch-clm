# Phase 16 Post-Reset Login Diagnosis — Independent Diagnostic Recheck

Date: 2026-09-21

Verdict: **PASS**

This verdict is limited to the safety and correctness of the frozen diagnostic
instrumentation and the truthfulness of its evidence report. It does not accept the
integrated application as fixed, waive the historical timeout, authorize merge, or turn
the successful non-reproduction into causal evidence.

## Reviewed identity and boundary

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`
- Branch: `phase/16-registry-cache-freshness-planning`
- Current source `HEAD`: `d8fc4ecd04459cfa4b39c920e9e67fab707eb039`
- Integrated `origin/main`: `bc21070fc1f45729e374a5cbe6425d89b8956ab9`
- Accepted Phase 16 head: `92cc8fa9f971a937b7f6696eb06f8675da7e9b05`
- Original Phase 16 `BASE_SHA`: `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Reviewed test-file blob: `52e3d86bf469c4754566980ad51e196dea7a227f`
- Reviewed diagnosis-report blob: `62a355bd19659b64ba09a827c49022e66b1851b8`

The reviewed paths were `tests/test_demo_lifecycle_windows.py` and
`.ai-pipeline/reports/PHASE_16_POST_RESET_LOGIN_DIAGNOSIS.md`. This reviewer wrote only
this assigned recheck. Production source, lifecycle scripts, configuration,
authentication, persistence, and the diagnosis report remained read-only. No lifecycle,
browser, Mongo, network, or broad-suite execution was performed by this review.

## Instrumentation and deterministic coverage

**PASS.** The authenticated `request()` helper records the requested bounded structural
fields at the real helper boundary: login versus target role, preparation/acquisition/
body/parsing completion stage, allowlisted before/after context, header/body/parse
completion, available status, sanitized failure category, monotonic elapsed
milliseconds, and target-dispatch state.

The implementation preserves exception type and propagation and adds only a sanitized
exception note. It does not retry login, synthesize a successful response, translate a
login timeout into the expected target `404`, or dispatch the target after a login
failure. The successful path still uses a fresh cookie jar, logs in as the existing
synthetic Director identity, applies the existing CSRF/origin behavior, and dispatches
the original target request.

The controlled transport tests exercise the real helper and cover every explicitly
requested deterministic case:

- successful login followed by the expected target `404`;
- timeout before login response headers;
- timeout during login body read;
- malformed login response;
- denied login through `HTTPError(401)`;
- successful login followed by target response-acquisition failure;
- no target dispatch after login failure;
- exact one-call or two-call counts, with no hidden retry; and
- preserved exception classes plus sanitized diagnostic records and exception notes.

Independent focused execution on the frozen blob passed all three selected test methods:
`3 passed in 3.36s`. Independent Ruff execution with its cache disabled also passed.

## Data minimization and unchanged behavior

**PASS.** Diagnostic records and notes contain no credential or hash, cookie, CSRF value,
response header/body, case identifier, URL, raw exception message, command line, or
environment dump. Caller-supplied context is reduced to the fixed allowlist. Exception
classification is an allowlist and the elapsed measurement uses `time.monotonic()`; no
client measurement is described as server CPU evidence.

The diff preserves the existing three-second request timeout, authentication payload,
fresh-cookie semantics, lifecycle health checks, memory-mode override, reset sequence,
pre-reset `200`, post-reset `404`, and session-identity assertions. Production
authentication, launcher, persistence, API/model/type, schema, connector, mapping,
business-rule, architecture-owner, and provider-status behavior is unchanged.

## Historical traceback and causal limits

**PASS.** The retained traceback is classified at the exact supported boundary:
`opener.open(login_request, timeout=3)` reached
`HTTPConnection.getresponse()` / `HTTPResponse._read_status()` and timed out waiting for
the response status line. That establishes login response acquisition before status or
headers; it excludes login-body read, login parsing, and target-request dispatch. The
report correctly does not call the event a case-deletion failure.

The Phase 13 event is kept distinct. Available retained repository evidence establishes
an intermittent timeout at the separate live-loopback `HttpSeedApi`/in-process service
boundary and later passing runs, but does not preserve an exact traceback stage that
would prove it matches the post-reset login timeout. The diagnosis therefore does not
claim a shared cause.

The cause remains correctly bounded to the system/runtime boundary. Authentication
latency, scheduling/resource contention, response transport handling, and another
transient runtime condition remain possible; none is promoted to an established root
cause. No timeout, scrypt, session, sleep, retry, launcher, or production correction is
proposed without new High-authorized scope.

## Physical lifecycle experiments and cleanup

**PASS as diagnostic evidence, not as a fix.** The report distinguishes the two allowed
experiments and their evidence revisions:

1. The first exact selector invocation, without prewarming, was blocked before reset or
   login by sandbox denial of Windows process-tree access. It proves only a process-
   permission prerequisite. Supported exact-owner cleanup then reported the partial
   process tree gone, ports 8000/5173 free, and the runtime manifest absent.
2. The second invocation tested the different, evidence-supported hypothesis that the
   first result was purely a sandbox process-management limitation. Under normal Windows
   process permissions, with the same memory-mode synthetic-auth composition and
   unchanged three-second timeout, the selector passed `1/1` in 49.159 seconds. Cleanup
   again left both ports free and no runtime manifest.

The report explicitly says that the passing run did not reproduce or fix the historical
timeout. It also discloses that the physical run preceded later deterministic assertion
strengthening and a diagnostic control-flow refactor; final focused tests cover the
frozen helper, and the authorized physical-run budget was not exceeded with a third run.

## Independent physical Mongo applicability

**PASS as a separate persistence lane.** Physical Mongo remains independently applicable
to the integrated Phase 16 persistence surface even though it cannot waive the lifecycle
failure. The reported guarded runner covers all five currently owned suites and records
`22` collected, `22` passed, and zero failures, errors, or skips. Repository inspection
confirms the runner's five-suite ownership and the generated allowlist for
`clm_p12_*`, `clm_p13_*`, `clm_p14_*`, `clm_p145_*`, and `clm_p16_*`; `clm_poc` is not
allowlisted. Each owned suite uses generated database names and verified cleanup.

The diagnosis records a task-owned localhost-only `mongo:7` container, no host data
directory or shared volume, URI confined to the test-process environment, verified
database cleanup, exact container removal, and a final container query. Those claims are
appropriately separated from lifecycle status and overall integration acceptance.

## Hygiene and findings

- Frozen test and diagnosis blobs matched the assigned identities before and after the
  focused review.
- `git diff --check` and staged diff checking passed.
- Both reviewed files have a final line feed and zero trailing-whitespace lines.
- Current source remains the uncommitted diagnostic delta at the recorded `HEAD`; no
  source revision is confused with the tested or reviewed content identity.
- Required fixes: **none**.

## Verdict and next authorized action

**PASS**

The frozen diagnostics are safe and correctly evidenced. The truthful overall state
remains **DIAGNOSIS INCOMPLETE — INTEGRATION BLOCKED** because the historical login
response-header timeout did not recur and no cause or correction was established. The
owner-authorized next action may be the separate diagnostic-only publication path to
the existing PR after the publisher revalidates the frozen blobs and clean committed-
tree pre-PR conditions. This recheck does not authorize a merge or final integration
acceptance.
