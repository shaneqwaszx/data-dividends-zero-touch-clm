# Phase 15C Lifecycle CI Stability Second Independent Recheck

Date: 2026-09-20
Role: independent focused reviewer
Change class: `CI_TOOLING`
Branch: `phase/15c-frontend-navigation`
Reviewed HEAD / baseline: `ff58edd80d14740e618019b0a8d598dec600419e`
Current `origin/main`: `4d1f646b3445c8d88df44dbc68abd109fe4d7aa5`

## 1. Findings

No critical, high, medium, or low findings remain in the final reviewed delta.

The verifier now performs one identity observation after both endpoint probes in each
polling attempt. It still verifies every expected launcher/listener identity before any
success return, detects replacement during either endpoint probe, and rejects each
endpoint independently when its completion time is later than the unchanged monotonic
deadline. No required fix remains.

## 2. Executive Result

**PASS**

The correction removes redundant verifier overhead without widening the five-second
endpoint deadline, changing the 0.1-second poll interval, weakening identity checks, or
adding lifecycle-action retries. Production lifecycle and application code are
unchanged.

This is an advisory independent recheck only. It does not authorize a commit, push,
pull request, merge, or next phase.

## 3. Acceptance Checklist

| Requirement | Result | Direct evidence |
|---|---|---|
| One identity observation per polling attempt | PASS | After both endpoint probes, `observe_owned_identities()` is called exactly once at `tests/test_demo_lifecycle_windows.py:706`. The deterministic two-attempt path observed 12 identity-probe calls: four expected launcher/listener records times one initial observation plus two attempt observations. Pre-fix evidence observed 20. |
| Identity verified before accepting success | PASS | The post-probe identity observation runs before the deadline check and before `all(last_endpoint_status.values())` can return. Any mismatch calls `self.fail`; success cannot bypass identity verification. |
| Replacement during either endpoint probe detected | PASS | Both probes complete before the single identity observation. A replacement introduced during either backend or frontend probing is therefore present when the observation runs and is rejected. Fresh in-memory adversarial runs rejected both placements. |
| Missing/dead process remains fail-closed | PASS | Missing observed identity still makes `_same_process_identity` false and `observe_owned_identities` fails. Fresh adversarial execution rejected an absent frontend PID. |
| Changed PID remains fail-closed | PASS | `_same_process_identity` still requires numeric PID equality. Fresh adversarial execution rejected a changed PID. |
| Changed executable remains fail-closed | PASS | The unchanged helper still requires case-normalized executable equality. Fresh adversarial execution rejected a changed executable. |
| Creation-time safety remains fail-closed | PASS | The committed shared helper and `<= 1 ms` integer-tick boundary are unchanged by this delta. Fresh adversarial execution rejected `1.0001 ms`; creation-time matrix passed 3/3. Malformed and timezone-less inputs remain rejected. |
| Same-PID launcher/listener safety preserved | PASS | All expected launcher and listener records are checked against the post-probe PID-keyed observation before return. The shared helper remains the only Python identity comparator. |
| Per-endpoint no-late-success preserved | PASS | Each endpoint's completion time is captured immediately after its probe. `any(completed_at > deadline ...)` fails before success. Fresh adversarial execution independently rejected late backend and late frontend completions. |
| Both endpoints still required | PASS | `all(last_endpoint_status.values())` remains the only success condition; the existing deterministic recovery path still polls and requires backend plus frontend health. |
| Timeout and polling interval unchanged | PASS | Defaults remain `timeout=5.0` and `poll_interval=0.1`. The diff changes no timeout, sleep, wait, or deadline value. |
| No retry-until-green behavior added | PASS | The existing bounded endpoint polling loop remains controlled by the same monotonic deadline. No lifecycle action, process launch, reset, stop, or unbounded retry was added. |
| Production code unchanged | PASS | Diff from `ff58edd80d14740e618019b0a8d598dec600419e` contains only the lifecycle test and remediation evidence. `scripts/demo_lifecycle.ps1`, `.github/**`, `apps/**`, and `scripts/**` have no diff. |

## 4. Contract and Integration Findings

The final delta changes only test-verifier scheduling. It does not change an API,
model/type, persistence schema, connector, configuration, business rule, mapping,
authentication/security boundary, architecture owner, provider status, frontend or
backend production behavior, or external integration claim.

The five-second bound continues to govern endpoint completion. Identity verification
may finish after an on-time endpoint completion because it is verifier overhead, but it
must still complete successfully before the test accepts health. This is the intended
and bounded distinction established by the remediation: instrumentation latency no
longer converts an already on-time endpoint result into a false late result, while a
late backend or frontend probe still fails.

ACRA remains Mock by default, GoldTier remains Mock only, and this recheck does not
establish Live provider readiness.

## 5. Tester and Adversarial Findings

Fresh reviewer evidence:

- In-memory verifier matrix using the production test method: PASS. It independently
  rejected replacement during backend probing and frontend probing; late backend and
  frontend completion; absent identity; changed PID; changed executable; and a
  `1.0001 ms` creation-time delta.
- The same matrix proved the transient two-attempt path called the injected identity
  probe 12 times, matching four expected identity records across one initial plus two
  per-attempt observations.
- `python -m pytest -p no:cacheprovider tests/test_demo_lifecycle_windows.py::DemoLifecycleCreationTimeTests -q`
  -> `3 passed in 1.90s`.
- `python -m ruff check --no-cache tests/test_demo_lifecycle_windows.py`
  -> `All checks passed!`.
- `git diff --check` -> PASS, with only informational LF-to-CRLF working-copy warnings.

Coordinator-provided fresh post-fix evidence:

- bounded/hostile focused selector: `1/1 PASS in 39.460s`;
- exact new CI failure selector: `1/1 PASS in 26.223s`;
- complete lifecycle suite, run once: `18/18 PASS in 268.524s`;
- creation-time matrix: `3/3 PASS`;
- governance unit bundle: `79/79 PASS`;
- direct project-state, architecture, tooling, and secret checks: PASS;
- Ruff and diff check: PASS.

The full 18-test lifecycle suite was deliberately not rerun by this reviewer.

Fresh CI evidence at committed head `ff58edd80d14740e618019b0a8d598dec600419e`
showed push run `35480722245` failing only lifecycle job `105997906007`, while PR
run `35480723978` passed all jobs. The earlier repeated-start/reset identity failure
passed in both. The new push failure had both endpoints healthy and every
launcher/listener identity true, but the frontend probe was reported late only because
the previous implementation ran a redundant PowerShell/CIM observation between the
two endpoint probes. The reviewed working-tree correction directly removes that
redundancy while retaining the endpoint completion timestamps and all identity checks.

## 6. Code and Architecture Review

The control flow is now:

1. perform the existing initial identity observation;
2. establish the unchanged monotonic deadline;
3. probe backend and frontend, recording each completion time immediately;
4. perform one post-probe observation of all expected launcher/listener identities;
5. reject any late endpoint completion;
6. return only if both endpoints are healthy; otherwise continue within the existing
   bounded polling loop.

That order is safety-preserving. Moving the identity observation after both probes
increases coverage of the attempt's full probe interval: any irreversible process
replacement during either probe is visible before return. The observation remains
batched by unique PID on the real CIM path. No new owner, fallback, duplicate identity
comparison, broad timeout, or production hook was introduced, and no ADR is required.

## 7. Security Review

No security finding was identified. The change does not alter process termination,
production ownership decisions, command-line inspection, logging, credentials,
authentication, provider transport, TLS, or external data handling. PID, executable,
creation-time, launcher, and listener verification remain fail-closed before success.

No secret or confidential artefact was added by the reviewed delta or remediation
report.

## 8. Required Fixes

None.

## 9. Readiness

The final bounded Phase 15C lifecycle CI stability remediation is ready for owner
review and the next authorized integration step. This PASS is not merge authorization
and does not establish real ACRA, PingFed, or GoldTier readiness.

## 10. Git Status and Review Boundary

- Branch: `phase/15c-frontend-navigation`.
- HEAD remained `ff58edd80d14740e618019b0a8d598dec600419e`.
- Current local `origin/main`: `4d1f646b3445c8d88df44dbc68abd109fe4d7aa5`.
- Starting unstaged delta: modified
  `.ai-pipeline/reports/PHASE_15C_LIFECYCLE_CI_STABILITY_REMEDIATION.md` and
  `tests/test_demo_lifecycle_windows.py`.
- Staged files: none.
- Untracked files at review start: none.
- This recheck overwrote only
  `.ai-pipeline/reports/PHASE_15C_LIFECYCLE_CI_STABILITY_RECHECK.md`, as authorized.
- No implementation, test, configuration, or other documentation file was edited by
  the reviewer. No commit, push, pull request, merge, branch operation, or next phase
  was performed.

## 11. Final Verdict

**PASS**
