# PR #42 Windows Lifecycle Diagnostic-Only Independent Recheck

Date: 2026-09-20
Role: fresh independent focused reviewer
Change class: `CI_TOOLING`

## 1. Findings

No critical, high, medium, or low findings were identified in the frozen diagnostic-only
delta.

- **Design Defect:** none. The structured endpoint probe remains inside the existing
  Windows lifecycle test owner and does not create a production owner, fallback, retry,
  or competing lifecycle contract.
- **Implementation Drift:** none. The delta is limited to sanitized test-verifier
  observability and deterministic coverage. It does not claim or implement a correction
  for the historical CI failure.
- **Required fixes:** none.

The historical root cause remains unknown. Stable process identities establish only that
the recorded launcher/listener identities remained present; they do not establish why
the historical frontend HTTP probe failed.

## 2. Verdict

**PASS**

This verdict applies only to publication of the frozen diagnostic-only content. It is
not a PASS for a lifecycle failure fix, does not waive the failed PR check, and does not
establish merge readiness for a correction. The diagnosis boundary remains:
**DIAGNOSIS INCOMPLETE — CI BLOCKER REMAINS**.

## 3. Reviewed content identity

- Worktree:
  `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-review-rework-ui`
- Branch: `followup/review-rework-ui`
- Original task base: `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Published feature head: `bc156dd1347425018a21e30b190feba288fdd524`
- Latest integrated main: `5f31aced13bd99df78329c5a9055cffaeb168ddd`
- Committed base/current HEAD before the diagnostic delta:
  `0603753c0c36a797d797a07b283d357421014619`
- Reviewed implementation path: `tests/test_demo_lifecycle_windows.py`
- Reviewed task-owned evidence path:
  `.ai-pipeline/reports/REVIEW_REWORK_UI_LIFECYCLE_CI_DIAGNOSIS.md`
- Test-module working-tree diff identity, computed from
  `git diff 0603753c... -- tests/test_demo_lifecycle_windows.py`:
  `de46cdbed85083e3917d3d6ef92d8ffe87594eca`
- Test-module working-tree blob: `12b41c0602e9045e9e3c763d807d343de21fabbe`
- Diagnosis-report blob: `c04bbdfd3d7a124b55e2a9d666fd161f8ae5e361`
- Staged paths: none.

At review start, Git status contained only the modified lifecycle test and the untracked
diagnosis report. This review added only this authorized recheck report. No branch switch,
fetch, stage, commit, push, merge, physical lifecycle run, browser workload, or production
file edit was performed.

## 4. Acceptance review

| Requirement | Result | Evidence |
| --- | --- | --- |
| Causal claim limits | PASS | The report distinguishes historical facts from inference, states that the old Boolean probe erased the next causal edge, and leaves the root cause unknown. It does not label the event a flake or attribute it to Vite, the server, the verifier, proxying, redirects, or process ownership. |
| Five-second recovery deadline | PASS | The default remains `timeout=5.0`; the deadline is established after the unchanged pre-deadline identity observation. Each endpoint completion is timestamped, an overrun is relabelled `deadline_overrun`, and any late endpoint completion fails before success. The poll interval remains `0.1` seconds and no lifecycle-action retry was added. |
| Original identity/timestamp semantics | PASS | The same expected launcher/listener PID, UTC creation timestamp, and executable path feed the unchanged `_same_process_identity` comparison. Identity verification still occurs before any success return and a mismatch fails immediately. |
| HTTP 200 and completed body for both endpoints | PASS | The default structured probe sets `healthy` only after response headers and body complete and status equals 200. Non-200, body failure, transport failure, timeout, and deadline overrun cannot satisfy `all(last_endpoint_status.values())`. Backend and frontend remain separately required. |
| Late success rejected | PASS | Completion time is captured per endpoint. A probe that reports success after the deadline becomes `deadline_overrun`; the deterministic regression rejects this path. |
| Safe diagnostics | PASS | Runtime observations contain endpoint role, status, allowlisted failure category, header/body completion flags, elapsed/remaining milliseconds, attempt, and identity presence/equality facts. They do not include response bodies, raw exception text, arbitrary URLs, command lines, environment values, authentication data, browser artifacts, or provider/case/document payloads. |
| Bounded diagnostics | PASS | Observation accumulation is bounded by the existing five-second loop, 0.5-second per-request cap, and 0.1-second polling interval. No unbounded retry, trace, screenshot, HAR, or production logging was introduced. |
| Existing owners and retirement | PASS | `endpoint_available` remains the ordinary Boolean helper for other lifecycle assertions. The new structured probe is used only by the targeted recovery verifier where failure-stage evidence is required. This is a justified diagnostic specialization, not duplicated production responsibility or a second process-ownership owner. No old owner is retired. |
| Scope and accepted UI/auth behavior | PASS | The working-tree implementation diff contains only `tests/test_demo_lifecycle_windows.py`. `scripts/demo_lifecycle.ps1`, launcher scripts, `.github/**`, `apps/**`, Vite configuration, frontend lockfile, accepted UI/auth/session behavior, dependencies, configuration, timeout values, and production behavior have no delta. |

## 5. Historical and physical evidence boundary

The supplied diagnosis records exact GitHub evidence for failed PR checkout
`6d2012772ab684feb46addeb2be97c832e6e81e4` and passing push checkout
`bc156dd1347425018a21e30b190feba288fdd524`, both with tree
`3e5324dae69e6766b682abb9fa3688b91b486701`, plus matching relevant blobs and runner/runtime
facts. The historical failure remained one of 18 tests, with six attempts, backend true,
frontend false, and all recorded identities stable.

The implementer-provided physical evidence is one valid exact-selector run passing in
41.602 seconds with ports/state cleaned afterward. That run did not reproduce or explain
the CI failure. Per the review assignment, this reviewer did not rerun a physical
lifecycle or browser workload and does not upgrade that non-reproduction into causal
evidence.

## 6. Fresh reviewer checks

- Deterministic diagnostic selectors:
  `python -B -m pytest -p no:cacheprovider` for
  `test_endpoint_probe_classifies_sanitized_failure_stages` and
  `test_endpoint_recovery_reports_bounded_structural_diagnostics`
  -> **2 passed in 2.87s**.
- Focused lint:
  `python -m ruff check --no-cache tests/test_demo_lifecycle_windows.py`
  -> **All checks passed**.
- Tracked implementation whitespace:
  `git diff --check 0603753c... -- tests/test_demo_lifecycle_windows.py`
  -> **PASS**, with only the informational LF-to-CRLF working-copy warning.
- Task-owned untracked report hygiene was inspected with `git diff --no-index --check`.
  It reported only the intentional two-space Markdown hard breaks on the Date and Change
  class lines; no unsafe or implementation-affecting hygiene issue was found.

The reviewer did not run the full lifecycle suite or a physical selector, as explicitly
prohibited by the assignment. Existing full/physical evidence is recorded as supplied
evidence rather than fresh reviewer execution.

## 7. Architecture, security, and compatibility conclusion

No API/model/type, persistence schema, connector, configuration, business rule, mapping,
authentication/security, architecture, provider status, frontend, production lifecycle,
or dependency behavior changes. No ADR or owner retirement is required.

The diagnostic path is fail-closed and preserves the accepted lifecycle guarantees:
both loopback endpoints must complete healthy responses within the existing endpoint
deadline, the original owned process identities must remain stable, malformed metadata
rejection is unchanged, and late health cannot retroactively pass. The retained Boolean
probe outside this verifier is compatible with its existing callers.

## 8. Remaining risk and next authorized action

The diagnostic delta can classify a future recurrence, but it cannot reconstruct the
failure stage erased by the historical Boolean output. The active historical cause
therefore remains unknown, and no timeout, launcher, Vite, application, workflow, or CI
correction is justified by this evidence.

The owner may decide whether to publish this exact diagnostic-only content under an
explicit no-fix/root-unknown claim. Any content change, causal-fix claim, production
lifecycle change, or latest-main integration that changes reviewed semantics requires a
fresh independent review. Human owners retain PR approval and merge authority.
