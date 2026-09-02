# RQG-03 — Windows Lifecycle UTC Ownership Remediation

Date: 2026-09-02  
Outcome: **READY FOR WINDOWS LIFECYCLE UTC OWNERSHIP INDEPENDENT QUALITY GATE.**

## 1. Executive summary

The creation-time comparison now preserves `DateTime`, `DateTimeOffset`, and explicit-offset ISO-8601 values as instants and compares them on one UTC timeline. The eager `[string]` conversions that stripped `DateTime.Kind` under PowerShell 7 were removed from launcher and listener ownership checks. The existing one-millisecond precision tolerance and all executable, command, ancestry, PID, and port checks remain intact.

The focused UTC+08 regression was RED before the production change and passed afterward. Continuation verification completed after the user stopped the protected UI V2 servers: both required 20-run loops passed, the complete Windows lifecycle suite passed, a separate PowerShell 7 Start → Status → Stop run passed with both health endpoints returning 200, two complete backend runs passed, and all requested ordering, phase, contract, static, dependency, GoldTier, and security checks passed. All changes remain bounded and unstaged.

## 2. Worktree / branch

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-lifecycle`
- Branch: `fix/windows-lifecycle-utc-ownership`
- Starting worktree: clean
- Changes: unstaged

## 3. Starting HEAD

`8309486da5784410791b77f9d4fdeb44fb0dd28c`

## 4. origin/main reference

`8309486da5784410791b77f9d4fdeb44fb0dd28c` at task start. Starting `HEAD` exactly matched `origin/main`.

## 5. Original RQG-03 finding

In `Singapore Standard Time` (UTC+08), an owned backend and frontend remained live and healthy, but PowerShell 7 `Status` returned `MISMATCH`. A stored UTC timestamp became a `System.DateTime` during JSON deserialization, then an eager `[string]` cast discarded `Z`/`Kind`; invariant reparsing interpreted the zone-less value as local time and shifted the instant by eight hours.

## 6. Existing lifecycle architecture

`start_demo_windows.bat` invokes `demo_lifecycle.ps1 -Action Start`. The controller starts fixed backend/frontend launchers, captures their identities, writes `STARTING` state, discovers descendant listeners, verifies health, writes `RUNNING` state, and later uses the same state for `Status`, `Stop`, and `Reset`. Stop authorizes only an exactly verified launcher or its separately recorded, exactly verified listener.

## 7. Timestamp serialization flow

Both CIM and `Get-Process` fallback identity acquisition call `ToUniversalTime().ToString("O")`. Launcher and listener records persist these unambiguous round-trip UTC strings through `ConvertTo-Json`. This format was already correct and remains schema version 1.

## 8. Timestamp deserialization flow

`Read-DemoState` uses `ConvertFrom-Json`. Windows PowerShell 5.1 returns the ISO field as `System.String`; PowerShell 7.6.4 returns it as `System.DateTime` with `Kind=Utc`. The new normalizer accepts either representation without an intermediate display-string conversion. A `DateTime` with `Kind=Unspecified`, a zone-less string, an unsupported type, null, or an invalid timestamp fails closed.

## 9. Reproduced UTC+08 failure

Environment diagnostics under PowerShell 7.6.4 and `Singapore Standard Time` observed:

- deserialized type: `System.DateTime`;
- kind: `Utc`;
- round-trip value: `2026-09-02T09:37:01.1234567Z`;
- `[string]` value: `09/02/2026 09:37:01`;
- reparsed kind: `Unspecified`;
- reparsed UTC: `2026-09-02T01:37:01.0000000Z`.

The focused pre-fix test compared that stored timestamp with `2026-09-02T17:37:01.1234567+08:00`. Result: `1 failed, 1 passed`; the same-instant assertion was the failure.

## 10. Root cause

The exact loss occurred at the `[string]` parameter binding in `Test-SameCreationTime` and at eager `[string]$Record.creation_time_utc` / listener call-site casts. PowerShell 7 had already preserved the UTC instant as a typed value, but the display-string conversion removed its timezone semantics before reparsing.

## 11. Chosen time representation

`System.DateTimeOffset` is the comparison representation. Typed `DateTimeOffset` values normalize directly. Typed `DateTime` values must have `Utc` or `Local` kind and are converted without stringification. Strings must carry `Z` or an explicit `±HH:mm` offset and are parsed with invariant culture and round-trip styles.

## 12. Ownership comparison design

`ConvertTo-UtcCreationInstant` normalizes both operands to UTC `DateTimeOffset`. `Test-SameCreationTime` computes the absolute millisecond difference and returns false on every normalization/parsing exception. No timestamp failure is accepted automatically.

## 13. Existing tolerance assessment

The existing tolerance is one millisecond, justified by the documented sub-microsecond precision difference between `Win32_Process` and `Get-Process`. It was retained unchanged. UTC offset differences normalize to zero and are not hidden by tolerance.

## 14. Launcher ownership

`Confirm-OwnedProcess` passes the recorded value in its actual deserialized type. Creation time, executable path/name, backend virtualenv path, and available command markers remain required. Status uses this path for backend and frontend launcher records.

## 15. Listener ownership

`Confirm-OwnedListener` uses the same instant-safe comparison for listener creation time and for rechecking the launcher before ancestry enforcement. Listener PID, executable, role markers, and available ancestry remain required.

## 16. Status behavior

Focused comparison behavior and actual Status are corrected. In the independent manual lifecycle, PowerShell 7 reported backend PID 46508 and frontend PID 46240 as `OWNED`; Status exited 0. The complete lifecycle suite also exercised this PowerShell 7 Status path with no false mismatch.

## 17. Stop behavior

Production logic remains fail closed: listener mismatch or an uncorroborated launcher mismatch retains metadata and terminates nothing. The hostile-metadata runtime test corrupted both launcher and listener timestamps with a wrong instant and malformed text, required `MISMATCH`, retained state, and proved both endpoints remained healthy. After restoring only the original test-owned metadata, supported cleanup succeeded. The separate manual PowerShell 7 Stop exited 0, removed only recorded owned processes, cleared metadata, and left both ports free.

## 18. PID-reuse safety

PID-only matching was not introduced. Creation instant remains the first identity check, followed by executable and command identity. Valid same-PID/current-instant ownership passed in the real lifecycle. Same PID with wrong or invalid launcher/listener creation evidence returned `MISMATCH`, retained metadata, and terminated nothing. The wrong-executable test also passed. The separately recorded listener exception still stops only the verified listener when a handed-off launcher is absent/reused; it does not terminate the mismatched launcher.

## 19. Backward compatibility

Currently generated schema-version-1 timestamps (`ToString("O")`, UTC `Z`) work as PowerShell 5 strings and PowerShell 7 typed UTC dates. Explicit-offset strings are also supported. Ambiguous zone-less or malformed old values fail closed and require independent recovery; no metadata migration or manual deletion is introduced.

## 20. Files changed

- `scripts/demo_lifecycle.ps1`
- `tests/test_demo_lifecycle_windows.py`
- `.ai-pipeline/reports/WINDOWS_LIFECYCLE_UTC_OWNERSHIP_REMEDIATION.md`

## 21. Implementation details

The production diff adds one normalization helper, changes the comparison parameters from `string` to `object`, and removes four eager creation-time string casts across launcher/listener verification. Tests extract the real PowerShell functions through the PowerShell AST for isolated timestamp checks and extend the real lifecycle path to use PowerShell 7 for Status/Stop plus hostile metadata cases.

## 22. UTC+08 regression tests

Continuation focused result: `3 tests passed` in 1.225 seconds. This covers the same instant represented as UTC and UTC+08, a genuinely different instant, malformed input, and zone-less input.

## 23. Wrong-creation-time regression

The isolated comparison rejects a two-second-different instant. The real hostile-metadata runtime test also passed: the existing live launcher/listener PIDs paired with wrong or malformed creation timestamps produced `MISMATCH`; Status and Stop returned nonzero; metadata was retained; and the owned endpoints remained healthy until the test restored the original metadata and performed supported cleanup.

## 24. Lifecycle focused tests

The focused real-process safety selection passed `3/3` in 44.023 seconds: PowerShell 7 valid ownership/Stop, wrong or unparseable launcher/listener timestamps, and wrong executable rejection. The complete Windows lifecycle suite then passed `17/17`, with 0 failed and 0 skipped, in 170.003 seconds.

## 25. Repeated timezone test 20-run result

The exact UTC/UTC+08 same-instant regression ran in 20 consecutive independent Python processes: `20/20 PASS`, 0 failures.

## 26. Repeated PID-reuse test 20-run result

The exact wrong-creation-instant guard used by process ownership ran in 20 consecutive independent Python processes: `20/20 PASS`, 0 failures. Real-process coverage separately proved valid same-PID/current-time acceptance, wrong/invalid timestamp rejection, and wrong executable rejection.

## 27. Start → Status → Stop runtime evidence

The separate supported lifecycle passed:

- Start exit: 0; session `d118dc43-9eb5-49cc-a757-c2df13f926b3` reached `RUNNING`.
- Backend launcher/listener: PID `46508` / `37872`.
- Frontend launcher/listener: PID `46240` / `46240`.
- PowerShell 7 Status: backend `OWNED`, frontend `OWNED`, exit 0.
- PowerShell 7 Stop: exit 0; all three distinct recorded PIDs absent afterward.
- Metadata: `.runtime/demo-processes.json` absent after Stop.
- Ports 8000 and 5173: zero listeners after Stop.
- Final PowerShell 7 Status: `No launcher-owned demo session is recorded.`, exit 0.

## 28. Health endpoint evidence

During the independent manual lifecycle, backend `http://127.0.0.1:8000/health` returned 200 and frontend `http://127.0.0.1:5173/` returned 200 before Stop.

## 29. Backend full run #1

Repository-root invocation with `PYTHONPATH=apps/backend` and the backend pytest configuration: `714 passed`, `11 skipped`, `4 warnings` in 20.08 seconds; exit 0. The 11 skips are the environment-gated genuine-Mongo module.

## 30. Backend full run #2

The same command passed again: `714 passed`, `11 skipped`, `4 warnings` in 19.95 seconds; exit 0.

## 31. RQG-02 ordering non-regression

Four focused nodes passed: historical deterministic list, equal-timestamp case-ID tie, envelope-order independence, and memory/Mongo equal-timestamp parity. Result: `4 passed` in 0.75 seconds. No diff exists in `apps/backend/app/services/zero_touch_repository.py` or `apps/backend/app/persistence/repositories.py`.

## 32. Phase regressions

- Phase 09: `39 passed`.
- Phase 10: `52 passed`.
- Phase 11: `58 passed`.
- Pre-Phase 12: `32 passed`.
- Phase 12: `18 passed`, `11 skipped` genuine-Mongo tests.

`PHASE12_MONGO_URI` was unavailable; no Mongo result was fabricated.

## 33. Contracts/static/security

- Contract tests: `44 passed` in 0.409 seconds.
- Ruff over `apps/backend`, `scripts`, and `tests`: `All checks passed!`.
- Strict mypy with no incremental cache: `Success: no issues found in 73 source files`.
- `pip check`: `No broken requirements found`.
- GoldTier validator unit tests: `5 passed`.
- GoldTier example validator: exit 0, `NOT VALIDATED` because optional private sponsor archives were absent; no private file was read.
- Repository secret scan: passed with no supported secret patterns.
- Secret-scanner unit tests: `5 passed`.
- `git diff --check`: passed.

Initial sandboxed Ruff/mypy/secret-test attempts could not create cache/temp paths, and the first GoldTier unit attempt lacked its checked-in optional validation dependencies. The repository requirements were installed into the Git-ignored virtualenv and the affected checks were rerun with host filesystem permission; all qualifying reruns above passed.

## 34. ACRA/security boundary

No diff exists in `apps/backend/app/connectors/acra_bizfile_sandbox.py`, `scripts/check_secrets.py`, or `tests/test_check_secrets.py`. Q-012 remains OPEN. OAuth, auth, TLS, provider, logging, and external-call behavior are unchanged.

## 35. Frontend boundary

Tracked `apps/frontend/**` changes: 0. `npm ci` created only Git-ignored local dependencies needed for demo execution.

## 36. Diff audit

`git diff --name-status` contains only the lifecycle script and lifecycle test file; this requested report is untracked. `git diff --check` passes. The production change is limited to instant normalization and its existing ownership call sites. Frontend, ordering, ACRA, security tools, API contracts, persistence schemas, and unrelated implementation have no diff.

## 37. Git hygiene

All changes are unstaged. No add, commit, push, merge, rebase, reset, clean, stash, checkout, branch switch, or PR action occurred.

## 38. Remaining limitations

- Genuine Mongo tests remain skipped locally because `PHASE12_MONGO_URI` is unavailable.
- Optional private GoldTier example archives are absent, so the example scan reports `NOT VALIDATED` rather than reading any private material.

These are explicitly permitted environment limitations and do not affect the bounded lifecycle readiness result.

## 39. Readiness

| Metric | Result |
| --- | ---: |
| UTC ownership mismatches for same instant | 0 |
| Status ownership failures | 0 |
| Stop ownership failures | 0 |
| PID-reuse protection regressions | 0 |
| Wrong-creation-time false matches | 0 |
| Ownership parse-failure false matches | 0 |
| Timezone regression failures across 20 runs | 0 |
| PID-reuse regression failures across 20 runs | 0 |
| Windows lifecycle test failures | 0 |
| Backend full-suite failures across 2 runs | 0 |
| Ordering regressions | 0 |
| Phase regressions | 0 |
| Contract regressions | 0 |
| Security regressions | 0 |
| Frontend changes | 0 |
| Ordering implementation changes | 0 |
| ACRA changes | 0 |
| Security-tool changes | 0 |
| API contract changes | 0 |
| Persistence schema changes | 0 |
| Unrelated changes | 0 |

All required metrics are zero. The bounded remediation is ready for independent quality gate; this is not merge, push, or acceptance authority.

READY FOR WINDOWS LIFECYCLE UTC OWNERSHIP INDEPENDENT QUALITY GATE

## 40. GitHub Windows CI Follow-up

### Original CI failure

GitHub Actions ran commit `d9d17a0ea3ba397c8bc8f20a374297e0c9e0f49d` on the
`windows-latest` `demo-lifecycle-windows` job. The only lifecycle failure was:

`DemoLifecycleWindowsTests.test_start_stop_health_pids_and_unrelated_processes`

PowerShell 7 Status returned exit 1 and reported both launchers as `MISMATCH`:

- backend PID 6488;
- frontend PID 5576.

The surrounding lifecycle scenarios passed.

### Failed predicate and decision chain

`Show-DemoStatus` calls `Confirm-OwnedProcess` for each recorded role. A live process
can return `MISMATCH` at creation-time equality, recorded executable-path equality,
role executable-name equality, backend virtualenv-path equality, or available command
marker equality. The first failing predicate returns immediately.

The pushed commit contained the new PowerShell 7 lifecycle regression tests and the
remediation reports but did **not** contain `scripts/demo_lifecycle.ps1`. Inspection of
the exact committed file confirmed that CI therefore executed the old
`Test-SameCreationTime` string parameters and the eager recorded-timestamp string cast.
Under PowerShell 7, `ConvertFrom-Json` materializes the stored UTC timestamp as
`DateTime(Utc)`; the eager cast converts it to a zone-less display string, which is
reparsed as local time. Creation-time equality is therefore the failed ownership
predicate. Path, executable-name, and marker predicates were not reached in the failing
Status decision chain.

This is a commit-content omission, not evidence of cross-API timestamp precision beyond
the existing tolerance.

### Safe diagnostic evidence

The failing test now collects sanitized diagnostics only when PowerShell Status returns
nonzero. For each role it reports normalized recorded/observed launcher and listener
instants, absolute deltas, creation/path/marker/listener/ancestry booleans, closed-set
ownership status/reason text, PowerShell version, and Windows timezone ID. It does not
serialize command lines, paths, environment dumps, secrets, tokens, or payloads. The
hostile-metadata test independently exercises this diagnostic path and asserts that no
`command_line` field is emitted.

A bounded local diagnostic run on PowerShell 7.6.4 in `Singapore Standard Time`
reported, for both backend and frontend:

- launcher and listener status: `OWNED`;
- normalized recorded/observed delta: `0.0 ms`;
- creation-time match: `true`;
- executable/path match: `true`;
- command/role marker match: `true`;
- listener ownership match: `true`;
- launcher ancestry/corroboration match: `true`.

### CIM versus Get-Process precision

Ten independent test-owned processes were measured through both `Win32_Process` CIM
`CreationDate` and `Get-Process.StartTime`. Absolute UTC deltas ranged from `0` to
`0.0007 ms`. These measurements do not show a legitimate local need to widen the guard.

### Correction and tolerance decision

The correction is to include the already independently reviewed canonical
`scripts/demo_lifecycle.ps1` UTC normalization change in the branch, together with the
test-only safe diagnostics above. No lifecycle redesign, CI special case, assertion
weakening, skip, ownership-predicate removal, or unrelated subsystem change was made.

The creation-time tolerance remains exactly `1 ms`. There is no CI diagnostic evidence
supporting a wider value, and keeping the narrow guard preserves PID-reuse protection.

### Local results

- pre-edit exact-test reproduction with the corrected unstaged script: `5/5 PASS`;
- focused UTC normalization: `3 passed`;
- focused valid ownership, hostile timestamps, and wrong executable: `3 passed`;
- complete CI-equivalent Windows lifecycle suite: `17 passed`;
- exact previously failing test in consecutive independent processes: `20/20 PASS`;
- secret scan: passed;
- secret-scanner unit tests: `5 passed`;
- Ruff over the changed lifecycle test: passed;
- ports 8000 and 5173 and runtime state: clean after verification.

### GitHub rerun result

PENDING — the bounded correction has not yet been pushed. Local success alone is not
treated as final readiness.

NOT READY FOR WINDOWS LIFECYCLE CI RE-VERIFICATION
