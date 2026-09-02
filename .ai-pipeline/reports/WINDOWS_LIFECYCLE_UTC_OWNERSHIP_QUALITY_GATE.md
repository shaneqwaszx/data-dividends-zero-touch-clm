# RQG-03 — Windows Lifecycle UTC Ownership Quality Gate

Date: 2026-09-02

Gate type: Independent, review-only

## 1. Executive summary

**PASS.** The Windows lifecycle remediation preserves creation times as instants across
PowerShell 5.1 string deserialization and PowerShell 7 typed `DateTime`
deserialization. Same-instant UTC and UTC+08 values compare equal, ambiguous or invalid
values fail closed, the existing 1 ms tolerance is unchanged, and launcher/listener
ownership and Stop safety remain intact. All required executable checks passed.

## 2. Reviewed worktree

`C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-lifecycle`

All repository audit, source inspection, test, runtime, and report actions were
executed in this worktree. No source or runtime state in the primary or ordering
worktrees was changed.

## 3. Branch

`fix/windows-lifecycle-utc-ownership` — expected branch confirmed; no branch switch.

## 4. Starting HEAD

`8309486da5784410791b77f9d4fdeb44fb0dd28c`

## 5. origin/main reference

`origin/main` resolved to `8309486da5784410791b77f9d4fdeb44fb0dd28c`.
The worktree HEAD exactly matched the expected remediation baseline.

## 6. Working-tree inventory

Initial inventory:

- modified, unstaged: `scripts/demo_lifecycle.ps1`;
- modified, unstaged: `tests/test_demo_lifecycle_windows.py`;
- untracked implementation evidence:
  `.ai-pipeline/reports/WINDOWS_LIFECYCLE_UTC_OWNERSHIP_REMEDIATION.md`;
- staged files: 0;
- unexpected implementation changes: 0.

This quality-gate report is the only file created by the gate.

## 7. Original RQG-03 finding

PowerShell 7 `Status` reported valid lifecycle-owned processes as `MISMATCH` in
Singapore/UTC+08. The stored timestamp represented a UTC instant, but JSON
deserialization returned a typed `DateTime(Utc)` and an eager string conversion erased
its timezone/Kind before comparison.

## 8. Root-cause verification

The baseline function was extracted independently from `HEAD` and exercised in
`Singapore Standard Time`:

- PowerShell 7.6.4: `ConvertFrom-Json` produced `System.DateTime`, `Kind=Utc`;
  `[string]` produced `09/02/2026 09:37:01`; reparsing treated it as
  `Unspecified` and converted it to `2026-09-02T01:37:01.0000000Z`; the valid
  UTC/UTC+08 comparison returned `False`.
- Windows PowerShell 5.1.26100.9278: `ConvertFrom-Json` retained
  `2026-09-02T09:37:01.1234567Z` as `System.String`; the equivalent comparison
  returned `True`.

The pre/post diff confirms that the old `[string]` parameters and the eager casts at
launcher/listener call sites were the lossy boundary. The observed failure therefore
matches the reported eight-hour shift mechanism.

## 9. Implementation diff

The production change is bounded to one new helper,
`ConvertTo-UtcCreationInstant`, changing `Test-SameCreationTime` inputs from `string`
to `object`, and removing eager creation-time string casts at three existing launcher
and listener comparison call sites. No unrelated production refactor is present.

The test change adds focused instant comparisons, makes the valid runtime path execute
PowerShell 7 Status and Stop directly, adds hostile timestamp coverage, and strengthens
the pre-existing wrong-executable assertion.

## 10. Time representation review

`DateTimeOffset` normalized to UTC is the single comparison representation.
`DateTimeOffset` values retain their instant. `DateTime` values are accepted only with
`Utc` or `Local` Kind and retain their instant. Strings require a terminal `Z` or
explicit `+/-HH:mm` offset and are parsed invariantly with round-trip semantics.

Direct probes under both PowerShell versions confirmed typed UTC `DateTime`, local
`DateTime`, `DateTimeOffset`, UTC strings, and explicit-offset strings converge on the
same UTC timeline.

## 11. Serialization contract

Lifecycle metadata generation remains unchanged:

- CIM and `Get-Process` fallback identities use
  `ToUniversalTime().ToString("O")`;
- session creation time uses `UtcNow.ToString("O")`;
- timestamps are ISO-8601, round-trip safe, and explicitly UTC;
- `schema_version` remains `1`;
- lifecycle metadata schema changes: 0.

## 12. Deserialization contract

PowerShell 5.1 JSON strings and PowerShell 7 typed UTC `DateTime` values both reach the
same instant-preserving normalizer. Explicit-offset strings are accepted. Null,
unsupported types, malformed strings, zone-less strings, and `DateTime` values with
`Kind=Unspecified` throw inside the normalizer and are converted to a fail-closed
comparison result.

## 13. Ownership comparison

No eager display-string conversion remains in any `Test-SameCreationTime` call path.
`Confirm-OwnedProcess` and both creation-time comparisons in
`Confirm-OwnedListener` pass the deserialized value in its actual type. The comparison
returns false on every parsing/normalization exception.

## 14. 1 ms tolerance

The baseline and remediated code both use an absolute difference of `<= 1` millisecond.
No widening occurred. Independent probes under PowerShell 5.1 and 7 confirmed:

- exactly 1 ms: match;
- 1.1 ms: mismatch;
- UTC/UTC+08 same instant: match before tolerance;
- two-second difference: mismatch.

Ownership tolerance widening: 0.

## 15. Fail-closed safety

Ownership still requires creation instant plus the existing identity evidence:
launcher PID, expected executable path/name, backend virtualenv binding, command
markers where observable, listener PID/path/role markers, and ancestry corroboration
where available. Stop precomputes launcher and listener checks and refuses all unsafe
termination when either required ownership path mismatches. There is no PID-only,
parse-success fallback, blind listener acceptance, or termination-after-mismatch path.

Ownership-safety weakening: 0.

## 16. PowerShell version compatibility

Host evidence:

- PowerShell 7.6.4, `Singapore Standard Time`;
- Windows PowerShell 5.1.26100.9278, `Singapore Standard Time`.

The direct compatibility matrix passed under both versions for UTC strings,
explicit-offset strings, local/UTC `DateTime`, `DateTimeOffset`, exact tolerance,
over-tolerance mismatch, zone-less, malformed, null, unsupported, and Unspecified
inputs. The real supported lifecycle was exercised with PowerShell 7 Status and Stop.

## 17. UTC+08 focused regression

`DemoLifecycleCreationTimeTests`: **3 passed in 1.23s**. The required
`2026-09-02T09:37:01...Z` and `2026-09-02T17:37:01...+08:00` values compared as the
same instant. A two-second difference mismatched; zone-less and malformed values failed
closed.

## 18. UTC+08 20-run result

The same-instant UTC/UTC+08 node ran in 20 consecutive independent Python processes:
**20/20 PASS**, 0 failures.

## 19. Wrong-creation-time regression

The focused comparison rejected a genuinely different instant. Real-process hostile
metadata tests retained the same live PIDs but replaced launcher and listener creation
times with a wrong instant and malformed text; Status returned non-success/MISMATCH,
Stop refused termination, state was retained, and both health endpoints remained
reachable. The valid test-owned state was then restored and supported cleanup passed.

The wrong-executable test also passed and proved that an unrelated process with a
matching PID/creation time is rejected by the executable/role boundary and remains
alive.

## 20. PID-reuse 20-run result

The wrong-creation-instant comparison ran in 20 consecutive independent Python
processes: **20/20 PASS**, 0 failures. Same PID plus wrong or invalid creation evidence
therefore cannot authorize ownership.

## 21. Focused real-process safety tests

Required selection: **3 passed in 42.37s**.

- valid PowerShell 7 ownership, Status, Stop, and unrelated-process survival;
- wrong/malformed launcher and listener timestamps;
- wrong executable rejection.

An initial sandboxed run failed only because the gate host denied `.runtime` writes and
CIM access. The authorized host-permission rerun above is the qualifying product result.

## 22. Full Windows lifecycle suite

`tests/test_demo_lifecycle_windows.py`: **17 passed, 0 failed, 0 skipped in 166.71s**.

## 23. Launcher ownership

Both backend and frontend launcher records use the corrected typed comparison.
Independent manual PowerShell 7 Status reported both launchers `OWNED`. Wrong and
malformed launcher timestamps produced `MISMATCH` and blocked Stop.

Launcher ownership regressions: 0.

## 24. Listener ownership

Backend and frontend listener creation values use the same normalizer. The valid
PowerShell 7 Stop path verified and stopped both recorded listeners, including the
backend launcher/listener split. Wrong and malformed listener timestamps blocked Stop
while the live endpoints remained healthy.

Listener ownership regressions: 0.

## 25. Real Start → Status → Stop

Ports 8000 and 5173 were confirmed free and runtime metadata absent before launch.

- Start: exit 0; session `df3a120e-4730-4509-ab12-23de0fcfd876`; state `RUNNING`;
  schema version 1.
- Backend launcher/listener: PID 46488 / 46484.
- Frontend launcher/listener: PID 32844 / 32844.
- PowerShell 7 Status: backend `OWNED`, frontend `OWNED`, exit 0.
- PowerShell 7 Stop: exit 0; all three distinct recorded PIDs absent afterward.
- After Stop: both ports had zero listeners and `.runtime/demo-processes.json` was
  absent.
- Final Status: `No launcher-owned demo session is recorded.`, exit 0.

## 26. Health endpoint evidence

During the independent real lifecycle:

- `http://127.0.0.1:8000/health` returned HTTP 200;
- `http://127.0.0.1:5173/` returned HTTP 200.

## 27. Hostile metadata runtime test

The real-process test independently replaced both roles' launcher and listener
timestamps first with `1970-01-01T00:00:00.0000000Z` and then with
`not-a-timestamp`. For each case, Status was nonzero with two `MISMATCH` results; Stop
was nonzero and reported that ownership could not be established; corrupted state was
retained; live health remained available. Only the saved test-owned valid metadata was
restored, after which the supported stop path cleaned up successfully.

## 28. Stop safety

Valid owned processes stop successfully. A mismatched launcher, mismatched listener,
wrong executable, invalid timestamp, incomplete running record, or unowned port holder
does not authorize termination. The full suite also verified unrelated Python, Node,
and titled command processes survive valid lifecycle Stop.

Unsafe termination paths: 0.

## 29. Backward compatibility

Schema-version-1 state containing valid UTC ISO strings remains interpretable under
PowerShell 5.1 and PowerShell 7. Explicit-offset strings also work. Zone-less or
malformed legacy values fail closed. No schema migration or manual deletion requirement
was introduced.

## 30. Backend full run #1

Complete backend suite: **714 passed, 11 skipped, 4 warnings in 19.99s**, exit 0.

## 31. Backend full run #2

Complete backend suite: **714 passed, 11 skipped, 4 warnings in 20.11s**, exit 0.

The warnings were the pre-existing Starlette deprecation warning and deliberate
Pydantic malformed-input serialization warnings in provider-conformance tests.

## 32. RQG-02 ordering non-regression

The focused historical ordering, equal-timestamp case-ID tie, opposing envelope, and
memory/Mongo equal-timestamp parity selection passed: **4 passed in 0.74s**.

There is no lifecycle-task diff in
`apps/backend/app/services/zero_touch_repository.py` or
`apps/backend/app/persistence/repositories.py`. Ordering regressions and ordering
implementation changes: 0.

## 33. Phase regressions

- Phase 09: **39 passed**.
- Phase 10: **52 passed**.
- Phase 11: **58 passed**.
- Pre-Phase 12: **32 passed**.
- Phase 12: **18 passed, 11 skipped**.

Phase regressions: 0.

## 34. Real-Mongo status

`PHASE12_MONGO_URI` is unavailable.

**REAL MONGO VERIFICATION NOT EXECUTED LOCALLY.**

The 11 skips are the genuine-Mongo tests guarded by that prerequisite. No adapter or
mock evidence was substituted. This is an environment limitation, not an RQG-03
lifecycle failure.

## 35. Contracts/static/security

- Contract unittest discovery: **44 passed in 0.418s**.
- Ruff with repository cache disabled: **All checks passed**.
- Strict mypy with external temporary cache: **no issues in 73 source files**.
- `pip check`: **No broken requirements found**.
- GoldTier validator unit tests: **5 passed**.
- GoldTier example validator `--if-present`: exit 0, **NOT VALIDATED** because optional
  private sponsor archives are absent; no private file was read.
- `python scripts/check_secrets.py`: **passed**, no supported patterns found.
- Secret-scanner unit tests: **5 passed**.

The first sandboxed GoldTier unit attempt was denied permission to create its bounded
test fixture directory. The authorized rerun passed and cleaned the test fixture.

## 36. ACRA/security boundary

No diff exists in `apps/backend/app/connectors/acra_bizfile_sandbox.py`,
`scripts/check_secrets.py`, or `tests/test_check_secrets.py`. Q-012 remains OPEN. No
auth, OAuth, TLS, provider, external-call, logging, secret handling, or ACRA behavior
changed.

ACRA changes: 0. Security-tool changes: 0. Security regressions: 0.

## 37. Frontend boundary

`apps/frontend/**` changes: 0. No formatter, generator, build, or frontend source write
was performed by the gate.

## 38. API/persistence boundary

No backend API, DTO, domain, persistence, Mongo, recovery, CAS, GoldTier, or zero-touch
workflow file is changed. API contract changes: 0. Persistence schema changes: 0.

## 39. Diff quality

Manual review found one timestamp-normalization owner, no duplicate implementation, no
unused helper, no permissive catch, no hidden fallback, no culture-sensitive parsing,
no broadened tolerance, no debug logging, no test-only production behavior, and no dead
code. The production change is localized to normalization and the existing ownership
call sites.

## 40. Git hygiene

Final hygiene checks confirmed:

- branch and HEAD unchanged;
- staged files: 0;
- implementation commits: 0;
- pushes/PRs/merges/rebases/resets/cleans/stashes: 0;
- `git diff --check`: pass;
- `git diff --cached --check`: pass;
- implementation diff remains limited to the lifecycle script and Windows lifecycle
  test;
- the remediation report was not modified by this gate.

## 41. Findings

| Severity | Count | Finding |
| --- | ---: | --- |
| CRITICAL | 0 | None. |
| HIGH | 0 | None. |
| MEDIUM | 0 | None. |
| LOW | 0 | None. |
| INFO | 2 | Real Mongo URI and optional private GoldTier archives are unavailable locally. |

No current acceptance blocker or required fix remains.

## 42. Remaining limitations

- Real Mongo verification remains unavailable without `PHASE12_MONGO_URI`.
- Optional private GoldTier example validation remains unavailable because the sponsor
  archives are absent.
- This bounded lifecycle gate does not establish real ACRA, PingFed, or GoldTier
  readiness and does not close Q-012 or any sponsor dependency.

## 43. Final metrics

| Metric | Result |
| --- | ---: |
| Critical findings | 0 |
| High findings | 0 |
| Medium findings | 0 |
| UTC ownership mismatches for same instant | 0 |
| Status ownership failures | 0 |
| Stop ownership failures | 0 |
| Ownership tolerance widening | 0 |
| Ownership-safety weakening | 0 |
| Launcher ownership regressions | 0 |
| Listener ownership regressions | 0 |
| Unsafe termination paths | 0 |
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
| Lifecycle metadata schema changes | 0 |
| Frontend changes | 0 |
| Ordering implementation changes | 0 |
| ACRA changes | 0 |
| Security-tool changes | 0 |
| API contract changes | 0 |
| Persistence schema changes | 0 |
| Unrelated implementation changes | 0 |

All required metrics are zero.

## 44. Final verdict

The bounded RQG-03 fix is ready to integrate. This verdict does not authorize a commit,
push, merge, or next phase, and it does not imply real ACRA/GoldTier readiness.

PASS — READY TO INTEGRATE WINDOWS LIFECYCLE UTC OWNERSHIP FIX
