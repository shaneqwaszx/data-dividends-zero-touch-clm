# PR #42 Windows Lifecycle CI Diagnosis

Date: 2026-09-20<br>
Change class: `CI_TOOLING`<br>
Status: **DIAGNOSIS INCOMPLETE — CI BLOCKER REMAINS**

## Scope and revisions

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-review-rework-ui`
- Branch: `followup/review-rework-ui`
- Original base: `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Published feature head: `bc156dd1347425018a21e30b190feba288fdd524`
- Failed PR checkout: `6d2012772ab684feb46addeb2be97c832e6e81e4`
- Failed and feature tree: `3e5324dae69e6766b682abb9fa3688b91b486701`
- Integrated main / PR #40 squash: `5f31aced13bd99df78329c5a9055cffaeb168ddd`
- Current source commit before the diagnostic working-tree delta:
  `0603753c0c36a797d797a07b283d357421014619`
- Test-module working-tree diff identity before independent review:
  `de46cdbed85083e3917d3d6ef92d8ffe87594eca`

PR #40 was merged before diagnostic edits. Its incoming paths are the Camunda observer
contract/checker and reports. The blobs for `tests/test_demo_lifecycle_windows.py`,
`scripts/demo_lifecycle.ps1`, `apps/frontend/vite.config.ts`, and
`apps/frontend/package-lock.json` remained identical to the failed feature tree. The
merge had no conflict. PR #41 was not integrated.

## Capability and resource preflight

- Local runtimes: Python 3.12.10, Node.js 22.23.2, npm 10.9.8, PowerShell 7.6.5,
  GitHub CLI 2.101.0.
- Existing worktree environment was used; no sibling installation or worktree was
  inspected or borrowed.
- Initial tracked worktree was clean, no Git operation was active, and no other Codex
  agent was using the checkout.
- Ports 8000 and 5173 were initially free. No runtime manifest existed.
- GitHub run/job logs were available read-only through the authenticated CLI.
- The referenced `PR42_WINDOWS_LIFECYCLE_FAILURE_EXCERPT.md` was not present in the
  supplied attachment directory. The exact GitHub logs and task-supplied facts were used.

## Historical failure facts

Run `35508503869`, attempt 1, job `106072229719` checked out PR merge commit
`6d2012772ab684feb46addeb2be97c832e6e81e4`. The failing selector was:

`DemoLifecycleWindowsTests.test_wrong_or_unparseable_creation_time_fails_closed_for_status_and_stop`

The `creation_time='not-a-timestamp'` subcase failed in
`assert_owned_endpoints_healthy_within(original_state)`. The final available diagnostic
reported six attempts, backend healthy, frontend unhealthy, and matching identities for
the backend launcher/listener and frontend launcher/listener. The run executed 18 tests
in 174.403 seconds with one failure.

The comparison push run `35508480870`, attempt 1, job `106072168177` checked out
`bc156dd1347425018a21e30b190feba288fdd524` and passed the same 18-test module in
181.661 seconds. The jobs used the same runner version/image, Python, Node.js, npm, npm
cache key, source tree, lifecycle test blob, launcher blob, Vite config blob, and lockfile
blob. The passing run is comparison evidence only; it does not make the failure transient
or prove a cause.

Incidental warnings were the GitHub Actions Node 20 deprecation/forced Node 24 notices
for action internals and Node deprecation warnings from those actions. They occurred in
both jobs and were not promoted to a dependency or product defect.

## Verifier findings

The recovery window begins only after one pre-deadline process-identity observation.
Within the five-second window, the helper probes backend then frontend sequentially,
gives each request up to 0.5 seconds, observes all expected identities, and sleeps for at
most 0.1 seconds before retrying. A probe completed after the overall deadline cannot
satisfy recovery.

Before this diagnosis, the endpoint helper read the complete body before returning the
HTTP status and collapsed HTTP/transport/body-read failure into a Boolean. Its final
message retained only the last Boolean endpoint round. Therefore the historical log
cannot distinguish HTTP non-200, refused/reset transport, timeout, response-body
failure, verifier exception, or deadline overrun. Stable launcher/listener identities do
not prove that Vite served a healthy HTTP response.

`urllib.request.urlopen` retains its standard environment proxy-bypass and redirect
behavior. No evidence tied proxy or redirect behavior to this incident, so those
semantics were not changed. Response resources are now explicitly scoped by context
managers in the diagnostic probe.

## Bounded diagnostic delta

Only `tests/test_demo_lifecycle_windows.py` changed. The diagnostic probe records:

- endpoint role, never an arbitrary URL;
- HTTP status when received;
- allowlisted category: `healthy`, `http_non_200`, `connection_refused`,
  `connection_reset`, `timeout`, `transport_failure`, `response_body_failure`,
  `verifier_exception`, or `deadline_overrun`;
- whether headers and body completed;
- elapsed milliseconds and remaining overall budget;
- identity-observation duration and the existing presence/same-identity predicates.

It does not record response bodies, raw exceptions, command lines, environment values,
credentials, browser artifacts, or arbitrary URLs. The original success requirement is
unchanged: both endpoint responses must complete with HTTP 200 within five seconds while
all original process identities remain the same. Late success remains failure.

This is observability, not a correction of the historical failure. No production
launcher, application, authentication, Vite, dependency, workflow, timeout, process
ownership, UI, or accepted session-generation behavior changed.

## Evidence

- Deterministic diagnostic tests: 2 passed in 2.031 seconds.
  - classify non-200, refused/reset, timeout, body failure, and verifier exception;
  - prove sanitized structural output, deadline accounting, late-success rejection,
    identity predicates, and response cleanup.
- Focused lint: `python -m ruff check tests/test_demo_lifecycle_windows.py` passed.
- Syntax compilation: `python -m compileall -q tests/test_demo_lifecycle_windows.py`
  passed.
- Whitespace: `git diff --check` passed (Git emitted only the existing LF-to-CRLF
  checkout warning).
- First physical attempt was invalid as target evidence: sandbox process control blocked
  owned-process cleanup with `Access denied`. The retained launcher-owned state was
  cleaned with the repository stop script outside the sandbox.
- One valid physical run of the exact historical selector outside the sandbox passed in
  41.602 seconds. It did not reproduce or explain the CI frontend failure and was not
  repeated.
- After the run, the runtime manifest was absent and ports 8000/5173 were free.

## Causal conclusion and stop state

Observed cause ceiling: the historical frontend HTTP probe returned false for the final
recorded rounds while the recorded frontend process/listener identity remained stable.
The old Boolean diagnostic erased the next causal edge. The exact selector now passes
locally, so no server failure or verifier defect active in the historical incident was
established.

Root cause status: **still unknown**. Plausible HTTP failure modes remain disjunctive and
the historical active member cannot be identified. The evidence does not authorize a
timeout increase, weaker health predicate, process-alive substitution, launcher/Vite
change, retry of the lifecycle action/suite, or CI-policy change.

The diagnostic delta may make a future recurrence actionable. It must not be published
as a failure fix or used to waive PR #42's failed check. No commit, push, PR update, or
workflow rerun is justified until an independent focused review assesses this frozen
diagnostic content and the owner decides whether diagnostic-only publication is desired.
