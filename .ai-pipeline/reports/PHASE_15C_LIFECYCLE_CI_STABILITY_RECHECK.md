# Phase 15C Lifecycle CI Stability Independent Recheck

Date: 2026-09-20
Role: independent focused reviewer
Change class: `CI_TOOLING`
Branch: `phase/15c-frontend-navigation`
Reviewed HEAD / assigned baseline: `3abecd673726200e8bcd8eb333c7d384d798eb57`
Current `origin/main`: `4d1f646b3445c8d88df44dbc68abd109fe4d7aa5`

## 1. Findings

No critical, high, medium, or low findings remain in the reviewed lifecycle CI
stability remediation.

The remediation applies the production lifecycle's `<= 1 ms` creation-instant
equivalence to the Python post-rejection verifier without weakening PID,
executable-path, process-presence, launcher, or listener replacement protection.
No required fix remains.

## 2. Executive Result

**PASS**

The tracked working-tree delta is limited to
`tests/test_demo_lifecycle_windows.py`. The production lifecycle controller is
unchanged, the former inline raw-string comparison is retired, one shared Python
identity helper owns the comparison, and focused independent execution passed.

This is an advisory recheck only. It does not authorize a commit, push, pull request,
merge, or next phase.

## 3. Acceptance Checklist

| Requirement | Result | Evidence |
|---|---|---|
| Production lifecycle script unchanged | PASS | `git diff -- scripts/demo_lifecycle.ps1` returned no diff. `git diff --name-only` from reviewed HEAD names only the lifecycle test. |
| No Phase 15C production code changed | PASS | The only tracked unstaged delta is `tests/test_demo_lifecycle_windows.py`; staged content is empty. |
| Same creation-time contract as production | PASS | Production `Test-SameCreationTime` normalizes unambiguous instants to UTC and accepts absolute delta `<= 1 ms`. `_same_process_identity` compares integer 100 ns ticks with a `10,000`-tick inclusive boundary. |
| Equivalent UTC/offset/precision representations pass | PASS | Tests cover six- versus seven-digit UTC, UTC versus `+08:00`, sub-millisecond delta, and exactly one millisecond. Fresh focused creation-time run: `3 passed`. |
| More than one millisecond fails | PASS | `1.0001 ms` differs by `10,001` ticks and is rejected; the focused matrix passed. Integer ticks avoid rounding an over-boundary value down. |
| Malformed or timezone-less input fails closed | PASS | The parser requires a terminal `Z` or bounded explicit offset and returns no identity match on missing, malformed, timezone-less, invalid-calendar, invalid-offset, type, or field errors. Focused tests passed. |
| PID reuse/process replacement protection remains | PASS | Identity still requires equal PID, valid creation instant, delta within tolerance, and case-normalized executable path. Changed PID, changed executable, absent process, over-tolerance time, replacement during probing, and dead process remain failure paths. |
| Same-PID launcher/listener is deterministic | PASS | Expected launcher and listener records for PID `201` are compared through the same helper against one PID-keyed observed identity in the real batched path. The deterministic pair asserts `[True, True]` for harmless representation differences and `[False, False]` for over-tolerance time, executable replacement, PID change, or disappearance. |
| Bounded endpoint recovery behavior unchanged | PASS | The diff does not change the monotonic deadline, `5.0 s` default timeout, `0.1 s` poll interval, per-endpoint identity recheck, endpoint recovery requirement, both-endpoint polling, or rejection of success completed after the deadline. |
| No timeout/retry weakening | PASS | No timeout, sleep, deadline, poll, retry, or endpoint-probe line changed. The helper replaces only the former inline identity predicate. |
| Old comparison retired | PASS | Search found no remaining inline raw creation-time equality in the verifier. `_same_process_identity` is the single Python owner used by production-equivalence matrix tests and `observe_owned_identities`. |

## 4. Contract and Integration Findings

This remediation changes test verification semantics only. It does not change an API,
model/type, schema, connector, configuration, business rule, mapping, authentication or
security boundary, architecture owner, provider status, frontend/backend production
behavior, or external integration claim.

ACRA remains Mock by default, GoldTier remains Mock only, and this lifecycle recheck
does not establish Live provider readiness.

The production comparison remains authoritative. The Python helper is intentionally
limited to the offset-bearing ISO strings emitted into lifecycle state and by the CIM
probe, and uses the same inclusive one-millisecond instant boundary.

## 5. Tester and Adversarial Findings

Fresh reviewer evidence:

- `python -m pytest -p no:cacheprovider tests/test_demo_lifecycle_windows.py::DemoLifecycleCreationTimeTests -q`
  -> `3 passed in 1.96s`.
- `python -m ruff check --no-cache tests/test_demo_lifecycle_windows.py`
  -> `All checks passed!`.
- Focused hostile ownership selector, rerun with the Windows process permissions it
  requires -> `1 passed in 43.47s`.
- `git diff --check` -> PASS, with only Git's informational LF-to-CRLF working-copy
  warning.

The first sandboxed attempt at the focused hostile ownership selector is excluded from
product evidence. It reached the real-process portion after its deterministic cases,
then failed startup cleanup solely because Windows process termination returned
`Access denied`. The repository's supported exact-ownership `Stop` action was run with
the required host permission and reported that every recorded launcher-owned process
tree was gone. Post-cleanup checks found no runtime manifest and zero listeners on
ports 8000 and 5173. The same focused selector then passed under the required host
permissions.

The complete 18-test lifecycle suite was deliberately not rerun by this reviewer.
Coordinator-provided fresh evidence records one post-remediation run at `18/18 PASS in
280.403s`, plus the exact prior failure at `1/1 PASS`, the focused bounded/hostile test
at `1/1 PASS`, and the creation-time matrix at `3/3 PASS`. That evidence is consistent
with the independently inspected source and the focused reruns above.

The coordinator-provided CI comparison is also consistent with a flaky test-side
contract mismatch: push run `35479055483` failed only Windows lifecycle job
`105993373958`, while PR run `35479069804` passed the same head tree. Both used the
same runner image and Python/Node/npm versions. No production-source delta explains
the different result.

## 6. Code and Architecture Review

The helper is local to the Windows lifecycle test and has one responsibility:

1. parse offset-bearing ISO creation times to integer UTC ticks;
2. compare the absolute delta to the production-equivalent inclusive one-millisecond
   boundary; and
3. combine that result with PID and executable identity.

The integer tick representation preserves the seventh fractional digit used by
PowerShell round-trip timestamps. Invalid input is converted to a false identity match,
not an exception or permissive fallback. There is no second raw comparison, fallback,
retry-until-green loop, timeout widening, production hook, or duplicate identity owner.

The change remains inside the existing test owner and does not meet ADR criteria.

## 7. Security Review

No security finding was identified. The change does not alter process termination,
production ownership decisions, command-line inspection, logging, credentials,
authentication, provider transport, TLS, or external data handling. Fail-closed
identity behavior is preserved for absent, malformed, over-tolerance, wrong-PID, and
wrong-executable observations.

No secret or confidential artefact was added by the reviewed delta or remediation
report.

## 8. Required Fixes

None.

## 9. Readiness

The bounded Phase 15C lifecycle CI stability remediation is ready for owner review and
the repository's next authorized integration step. This PASS is not merge
authorization and does not establish real ACRA, PingFed, or GoldTier readiness.

## 10. Git Status and Review Boundary

- Branch: `phase/15c-frontend-navigation`.
- HEAD remained `3abecd673726200e8bcd8eb333c7d384d798eb57`.
- Current local `origin/main`: `4d1f646b3445c8d88df44dbc68abd109fe4d7aa5`.
- Tracked unstaged implementation/test delta: only
  `tests/test_demo_lifecycle_windows.py`.
- Task-owned untracked remediation evidence:
  `.ai-pipeline/reports/PHASE_15C_LIFECYCLE_CI_STABILITY_REMEDIATION.md`.
- Staged files: none.
- This recheck created only
  `.ai-pipeline/reports/PHASE_15C_LIFECYCLE_CI_STABILITY_RECHECK.md`.
- No implementation, test, configuration, or ordinary documentation file was edited
  by the reviewer. No commit, push, pull request, merge, branch operation, or next
  phase was performed.

## 11. Final Verdict

**PASS**
