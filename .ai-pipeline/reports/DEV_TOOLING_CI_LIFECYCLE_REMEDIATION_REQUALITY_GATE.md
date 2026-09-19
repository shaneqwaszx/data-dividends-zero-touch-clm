# Development Tooling CI Lifecycle Remediation — Independent Re-Quality Gate

Date: 2026-09-20
Gate type: Independent focused re-quality gate
Change class: `CI_TOOLING`

## 1. Executive Result

**PASS.** The final test-only remediation removes the instant-sensitive lifecycle
assertion without weakening process-ownership or fail-closed Stop/Reset semantics. The
root classification is **B + C**: an instant-sensitive test assertion exposed by CI
timing/scheduling variability. It is not a production launcher defect.

No required fix remains. This result is **READY FOR FOLLOW-UP COMMIT/PUSH/FRESH CI**.
It is not merge authorization.

## 2. Phase Acceptance Checklist

| Requirement | Result | Direct evidence |
| --- | --- | --- |
| Classify the same-SHA CI discrepancy | PASS | On head `df6a1745f4b2cb84067934eaa1ae05f16bac754c`, GitHub run `35454265616` failed only the lifecycle test's exact one-shot frontend health assertion after rejected Stop, while run `35454254173` passed the lifecycle suite on the same SHA. |
| Preserve launcher ownership and fail-closed behavior | PASS | The helper compares original launcher/listener PID, UTC creation time, and executable identity before health success; missing, dead, or replaced identities fail. `scripts/demo_lifecycle.ps1` is unchanged. |
| Replace only instant-sensitive health observations | PASS | Running-health assertions use bounded endpoint polling with unchanged owned identities. No whole-test retry, blind sleep, global timeout increase, replacement process, skip, continue-on-error, or lifecycle removal exists. |
| Keep polling bounded and reject late success | PASS | A five-second monotonic health deadline, bounded per-probe HTTP timeout, and completion-time check reject a response completing after the deadline. |
| Preserve rejected Stop/Reset state and process behavior | PASS | Malformed timestamp and incomplete-running-state paths still require non-zero Status/Stop/Reset results, retained corrupt metadata, unchanged session identity where applicable, no fresh start after rejected Reset, and healthy original processes before safe cleanup. |
| Cover adverse identity and endpoint paths | PASS | Deterministic injected cases cover transient frontend recovery, permanent frontend outage, dead frontend, pre-probe replacement, replacement during probing, past-deadline health, and backend recovery/probing. |
| Consolidate running-health checks safely | PASS | All running-health call sites use the ownership-aware helper; stopped-state checks retain their separate shutdown assertion. |
| Keep the change test-only | PASS | The sole implementation delta is `tests/test_demo_lifecycle_windows.py`; production launcher code is unchanged. |

## 3. Contract and Integration Findings

No contract or integration finding remains.

The paired GitHub runs are authoritative because both observed the same PR head SHA.
The failing run isolates a one-shot frontend HTTP observation after the launcher had
already rejected unsafe Stop and retained state; the passing run demonstrates that the
same production code and test could complete successfully. This supports classification
`B + C` and does not support a launcher termination, ownership, or state-retention bug.

No API/model/type, durable schema, connector, configuration, business-rule, mapping,
authorization/security, architecture, or provider-status change is present. No sponsor
contract, provider claim, or Live-integration status is affected.

## 4. Tester and Adversarial Findings

Final evidence on the exact reviewed delta:

| Check | Result |
| --- | --- |
| Focused physical lifecycle selection | PASS — 5/5 in 144.057s |
| Complete Windows lifecycle suite | PASS — 18/18 in 313.671s |
| Tooling unit suite | PASS — 66/66 in 9.176s |
| Governance unit suite | PASS — 37/37 in 23.323s |
| Secret tests | PASS — 8/8 |
| Direct tooling checks | PASS |
| Direct project-state check | PASS |
| Direct architecture check | PASS |
| Direct secret checks | PASS |
| Ruff on the changed test | PASS |
| `git diff --check` | PASS |

Independent injected review also confirmed that replacement during an endpoint probe
and endpoint success after the monotonic deadline are rejected. The batched
`Win32_Process` identity reader performs one filtered query for all distinct expected
PIDs, handles empty/object/array result shapes, and maps observations by PID so a shared
launcher/listener PID is compared against every expected role record.

Permanent endpoint failure cannot pass, backend health remains checked on every
attempt, and identity loss or replacement terminates the assertion rather than waiting
for a different process to become healthy. The helper retries only the bounded health
observation; it does not replay Stop, Reset, Start, or the enclosing test.

Mongo, Chromium, and backend suites were not rerun because the delta changes only the
Windows lifecycle test harness and cannot affect persistence, browser orchestration, or
backend product behavior. Their omission is scope-based, not converted into evidence.

## 5. Code and Architecture Review

No code or architecture finding remains.

The change stays within the existing Windows lifecycle test owner. The helper has one
responsibility: prove that both endpoints recover within a small deadline while the
original owned launcher/listener identities remain stable. Single-query CIM collection
reduces diagnostic overhead without changing the identity tuple or production ownership
rules. Endpoint and identity diagnostics remain bounded and safe.

There is no new production fallback, compatibility path, service, dependency direction,
state owner, or architecture surface. The ordinary one-shot assertion is retired from
running-health call sites in favor of the stronger consolidated invariant.

## 6. Security Review

No security finding remains.

The change uses loopback health endpoints and local process metadata only. Diagnostics
contain roles, process IDs, presence, identity-match booleans, attempts, and endpoint
status; they do not expose command lines, credentials, tokens, request bodies, KYC/PII,
or confidential sponsor artefacts. Missing or unreadable process identity fails closed.
Production termination authorization is unchanged.

## 7. Required Fixes

None.

No accepted technical debt or later sponsor dependency is needed to satisfy this
focused remediation.

## 8. Readiness

The remediation is **READY FOR FOLLOW-UP COMMIT/PUSH/FRESH CI** by the authorized owner.
Fresh CI should confirm the committed SHA on GitHub. This gate does not authorize merge,
start another phase, or change branch history.

Real ACRA verification and real GoldTier integration readiness are unchanged and out of
scope. ACRA remains Mock by default with only the recorded partial sandbox seam, and
GoldTier remains Mock only.

## 9. Git Status

- Branch: `dev-tooling`.
- Pre-remediation HEAD: `df6a1745f4b2cb84067934eaa1ae05f16bac754c`.
- Last-fetched `origin/main` and merge base:
  `895544db3341507dde5c2b210194c22e73e5a024`.
- Tracked working tree after this report: the test delta in
  `tests/test_demo_lifecycle_windows.py` plus this independent report only.
- Staged files: none.
- Commit/push/merge performed by this gate: none.
- The owner will fetch and compare current `origin/main` again before publication.
- No implementation/test/configuration file was edited by this reviewer, and no next
  phase was started.
