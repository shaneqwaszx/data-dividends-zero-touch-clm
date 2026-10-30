# D-103 / D-105 integration quality gate: second bounded recheck (PR #138)

This is an independent Stage 3 bounded recheck (`fyp-quality-gate`) of the delta that followed
`.ai-pipeline/reports/D103_D105_INTEGRATION_REQG.md` (finding R1). The reviewer did not write
the reviewed content, the earlier gate, the first recheck, or the remediation. The review was
read-only. The only file created is this report.

## 1. Verdict

**PASS**

The delta is a comment-only fix plus the two earlier gate reports committed. R1 is resolved,
and the new comment matches the code. Behaviour is unchanged. No new finding.

## 2. Frozen identity

| Item | Value |
|---|---|
| Branch | `assistant-edits` |
| HEAD | `837402f7a6934f2fe21b458c24e299b70a05b040` (single parent `5ffaad3`) |
| Tree | `85fede8ff70ffd4441db6171264dfe49c4e5dcf4` |
| Previous reviewed HEAD | `5ffaad3834b74872cb39ef2babeae3eabad59170` |
| Local `origin/main` ref | `582ad666031c8f139bfc5ad254bcd03244c3d640`. Not fetched. `git rev-list --left-right --count origin/main...HEAD` gives `0 9`, so HEAD is 0 behind. |
| PR #138 | OPEN. `headRefOid` is `837402f7…`, the same as HEAD. |
| Working tree | Clean before this report was written. |

## 3. Delta reviewed (`git diff 5ffaad3 837402f`)

The delta touches 3 files, with 391 lines added and 1 removed:

- `apps/assistant/scripts/build_synthetic_eligibility.py:120-123`: comment only. One line is
  replaced by four. `NON_CASE_VIEWERS` (`:47`) and `viewers()` logic are unchanged.
- `.ai-pipeline/reports/D103_D105_INTEGRATION_QUALITY_GATE.md` (new, 263 lines): the first gate
  report. It keeps its own verdict, **PASS WITH MINOR FIXES**, and its HEAD `7981436`.
- `.ai-pipeline/reports/D103_D105_INTEGRATION_REQG.md` (new, 124 lines): the first recheck. It
  keeps its own verdict, **PASS WITH MINOR FIXES**, HEAD `5ffaad3`, and finding R1 with its
  original wording.

On the report files: their local mtimes (16:29, 16:41) are before the commit (16:47), and the
committed content matches the working tree. Neither report shows signs of softening. Each keeps
its verdict, its findings (L1 to L6, R1), its "required fix" section and its list of unavailable
checks. This reviewer cannot compare them byte for byte with the authors' original output. That
check is limited to content inspection.

No executable code, test, manifest, configuration or qualification-basis file changed.

## 4. Checks run (on `837402f`)

| Check | Result |
|---|---|
| `.venv/bin/python apps/assistant/scripts/build_synthetic_eligibility.py --check` | "synthetic eligibility is current" (exit 0) |
| `.venv/bin/python -m ruff check --no-cache apps/assistant/scripts` | All checks passed (exit 0) |
| `git diff --check 5ffaad3 837402f` | Clean (this also covers the two newly tracked reports) |
| Whitespace of this report | Checked separately |

All other evidence is reused from the gate on `7981436` and the recheck on `5ffaad3`. The delta
does not invalidate any of it.

## 5. R1 resolution, checked against the code

The new comment says:

1. "Leaving it out of this D-095 manifest means, in D-095 mode, those ticket chats are never
   sent to an external model." **True.**
   - Every external model sets `requires_synthetic_boundary = True`: the remote test model
     (`remote_test.py:286`), Claude (`anthropic_runtime.py:583`) and the D-104
     `SyntheticOnlyModel` (`data_access.py:119`).
   - So `main.py:771` sends them all through the gate.
   - In D-095 mode (`main.py:777-787`), `synthetic_eligibility_check` refuses because
     "Support User" is absent from `synthetic_eligibility.json` `viewers` (lines 262-269).
2. "Outside D-095 mode the synthetic boundary decides, and it lists every seeded user (Support
   included)." **True.**
   - Outside D-095 mode, `main.py:789` calls `synthetic_boundary_check`.
   - `synthetic_boundary.json:19-27` lists "Support User".
3. "so only the synthetic test case can reach an external model there." **True.** The boundary
   admits only prompts inside the verified synthetic seed. This matches R1's own analysis in
   the first recheck.

The comment no longer claims "local model only" in general, so the overstatement is gone. R1 is
**resolved**.

## 6. Owner dispositions (PR body)

The PR description still records findings 1 to 5 accurately as "Accepted", with the same
substance the first recheck verified. Finding 6 is recorded as fixed in `5ffaad3`.

Advisory note (not a finding against reviewed content): some PR body text is now out of date.
- It calls the gate report "not yet committed".
- It does not mention R1 or `837402f`.
- Its "Before merge" list still asks for the `5ffaad3` recheck.

The owner may want to update the PR description before merge.

## 7. Unavailable checks (carried forward, not passes)

| Missing | Blocked claim |
|---|---|
| Physical Mongo | That Mongo-mode startup seeds `support-user` once, never overwrites it, and fails closed, against a real driver and server. |
| Full official E2E / lifecycle suite | That the other browser journeys show no regression under the official runner. |
| Hosted CI (GitHub billing block) | The remote CI status of PR #138. |

## 8. Required fixes

None.

## 9. Git status

- Nothing was staged, committed or pushed, and no GitHub comment was posted.
- `.env` was not opened, and the dev servers on ports 8000, 5173 and 8100 were not touched.
- Only this report was created in the repository.
