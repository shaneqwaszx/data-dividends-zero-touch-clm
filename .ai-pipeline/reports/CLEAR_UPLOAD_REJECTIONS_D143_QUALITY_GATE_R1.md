# D-143 clear upload rejection reasons: quality gate R1

Reviewer: an independent Claude Code reviewer subagent. It did not write or fix any of the reviewed content, and it did not write the R0 review.
Date: 2026-11-18. Scope: bounded change D-143 (PROPOSED), "Specific, plain reasons when an upload fails the local document checks" (R1 to R4). Round R1: recheck of the R0 fix (F1) plus a fresh pass over the whole branch diff. Method: `.agents/skills/fyp-quality-gate/SKILL.md` read directly (the user authorised this instead of the Skill tool).

## Reviewed content (frozen)

- Worktree `/Users/tasha/Documents/GitHub/dd-clm-clear-upload-rejections`, branch `fix/clear-upload-rejections`, HEAD `701e46610323acc827e5a179dfe22013f17aa1f4`, tree `4772d6bf03c6acf507b0591a36710f2231d9bbcd`. The tree was clean at the start (`git status --porcelain --untracked-files=all` empty) and stayed clean, apart from this untracked report.
- Base used for review: `e73c85d1434b3e62b66b88c21b6d4c8eaef8a0d5` (the merge base; an ancestor of HEAD, confirmed).
- **Main has moved.** After `git fetch origin`, `origin/main` is `4e35c90e2d3f8ffab131dff7b1c8e584c7591c97` (#202, "remove retired assistant settings from release baseline"). It changes only `tools/release/policy/effective-baseline.json` (8 deletions), which this branch does not touch. `git merge-tree --write-tree HEAD origin/main` merges cleanly. VC-1, rerun against the new `origin/main`, gives the same result as before (section 3). The branch is 1 commit behind; this is a readiness item, not a gate finding.
- R0 to R1 delta: `8143e38` (adds the R0 report only) and `701e466` (F1: `App.tsx` line endings). `git diff --stat 98e96f0 8143e38` is the report only.
- Paths reviewed: all 19 from `git diff --name-only e73c85d...HEAD` (R0's 18 plus the committed R0 report).

## 1. Executive result

**PASS** for the gate's scope (code, tests, contract, architecture and security). F1 is fixed and no new finding requires a fix.

**Merge readiness is not granted by this verdict.** VC-1 still fails and needs Shane's decision (section 3). The branch must also merge the new `origin/main` (#202) and rerun pre-PR before the PR.

## 2. R0 fix verification (F1)

| Check | Expected | Result |
| --- | --- | --- |
| `git diff origin/main...HEAD --stat -- apps/frontend/src/App.tsx` (merge base e73c85d) | 15 insertions only | `15 +++++++++++++++` (15 insertions, 0 deletions) |
| `git diff --ignore-cr-at-eol 98e96f0 701e466 -- apps/frontend/src/App.tsx` | empty | empty (0 lines): no content change |
| CRLF line count in `App.tsx` | main's 2316 CRLF of 2436 lines + 15 new lines | HEAD 2331 CRLF of 2451 lines; all 15 inserted lines end in CRLF, matching their CRLF surroundings |
| Line-ending churn in any other branch file | none | `git diff --stat` and `git diff --ignore-cr-at-eol --stat` against e73c85d are identical for all 19 files (962+/50-). Per-file CRLF counts: `test_pre_phase12_workspace_multidoc.py` 827/880 on both sides; every other changed file 0 CRLF on both sides; new files are LF only |
| `git diff --check e73c85d...HEAD` | clean | clean |

F1 is closed.

## 3. Contract and integration findings

- **No change since R0.** `git diff 98e96f0 701e466 -- apps scripts`, ignoring CR at EOL, is empty. The API contract, exit-code mapping, wording table and banner behaviour are exactly what R0 reviewed.
- **Fresh pass over the whole diff (anything R0 missed).** I reread every hunk of `local_document_worker.py`, `local_process.py`, `local_document_runtime.py`, `idp.py`, `document_errors.py`, `document_media.py`, `document_processing.py`, `App.tsx`, `CaseDetail.tsx`, `uploadRejection.ts`, the new tests and the decision entry. Confirmed:
  - The worker's `try` in `_image` catches only `DecompressionBombError` / `DecompressionBombWarning`; every other exception, including `_Rejection`, passes through unchanged. `main()` handles `_Rejection` before the generic `except Exception`, so a key lookup is always into the fixed five-entry map.
  - `run_bounded_process` uses `failed_codes` only when the caller passes it; the OCR path does not, so its codes are unchanged.
  - `document_media.py` keeps the old sentence for codes outside the table; `document_processing.py` keeps the old sentence for stored failures outside the table.
  - `rejectedBeforeStorage` is `false` when the file key already has a stored failed document, including one from an earlier attempt. That keeps the existing retry flow, which is the conservative choice.
  - `rejection` reaches the banner only while `uploadRejection.forMessage === requestError`, and `resetOnboardingForm` clears it.
  - D-143 is still a free number: `origin/main` 4e35c90 does not add a D-143 (`git diff e73c85d origin/main -- docs` is empty).
- **VC-1 (owner decision; outside the gate's authority).** I reran `scripts/check_boundary_vocabulary.py` at 701e466 against `origin/main` 4e35c90: `FAIL_CHANGED_NOT_CURRENT`, `file_word_delta` code_vocabulary +7/-1, `head_drift` +77/-2, `base_drift` null. That matches R0 and the author's `up-pre-pr.log` on 701e466 (taken when `origin/main` was e73c85d). #202 did not change it. R0's D-094 review of the 8 words still applies (no boundary-file change since). The gate does not treat VC-1 as granted.
- **Release test.** `tests/release/test_source_images_render.py::test_backend_schema_version_is_read_from_the_commit` (21 == 20) was verified by R0 as main's own failure. The branch does not touch `tests/release`, `tools` or `models.py`. #202 changes only a release policy JSON. The gate does not treat it as granted.

## 4. Tester and adversarial findings

Environment: the worktree-only venv `<scratchpad>/venv-upload/bin/python`; the repo-root `.venv` was not used. Caches disabled (`-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`). The worktree stayed clean after every run.

Reviewer runs at 701e466:

- **Backend.** `pytest tests/test_upload_rejection_reasons.py tests/test_sf001_sf002_document_worker_hardening.py`: **38 passed, 1 skipped, 1 failed**. The failure is `test_a_real_child_process_sees_no_backend_secret`, the known macOS-only failure that also fails on main (`__CF_USER_TEXT_ENCODING`).
- **Frontend.** `tsc -b --noEmit`: exit 0. `vitest run src/pages/UploadRejectionBanner.test.tsx src/App.test.tsx`: **76 passed** (2 files).
- **VC-1.** As in section 3.

Author evidence on 701e466, checked against this HEAD: tsc 0, build 0, vitest `App.test.tsx` + `UploadRejectionBanner.test.tsx` + `Phase15CNavigation.test.tsx` 123 passed. Pre-PR on the clean tree (`up-pre-pr.log`: HEAD 701e466, ahead 8 / behind 0 at that time): every check PASS except VC-1, plus the `App.tsx` hotspot warning. Because F1 changed only line endings, R0's behavioural evidence (the HEAD-vs-main worker probe, full vitest, backend targeted runs, the affected E2E on 4f19691, and assistant per-file runs) still applies. I did not rerun full suites or E2E.

All evidence is local. CI is billing-blocked, and nothing here is hosted CI.

## 5. Code and architecture review

- **F1: fixed** (section 2).
- **R0 N1 (`DOCUMENT_STRUCTURE_INVALID` wording also covers non-file causes): I agree it is non-blocking.** The code mapping existed before D-143. Only the wording is new, and the suggested action ("choose a different file") is still a reasonable next step for the memory-cap case. A separate runtime code can be a later change.
- **R0 N2 (old sentence kept for codes outside the table): I agree it is non-blocking.** It matches R3's scope, and those codes are not file-content rejections covered by D-143.
- **N3 (new, informational, optional).** In `CaseDetail.tsx` the banner renders `rejection.lines.map(line => <p key={line} …>)`. If one upload holds two files with the same name and the same reason, the two lines are identical, so React warns about a duplicate key. Both lines still render. This is a development-time warning only, with no user-visible or security effect. A key that includes the index would avoid it. Not required.
- **Scope.** No scope creep. The R0→R1 delta is the report plus a line-ending-only change.

## 6. Security review

There are no security findings. Nothing changed since R0's security review (the R0→R1 code delta is line endings only). I rechecked it on the whole diff:

- the child sends only a fixed integer, and stderr is discarded;
- the parent builds every message from a fixed table;
- no document content, file name, object id or library text reaches the API;
- the file name in the banner is rendered as escaped React text;
- SF-001, SF-002 and every limit are unchanged;
- no auth, permission or maker-checker path is touched.

## 7. Required fixes

None for the gate.

Outside the gate's authority (not fixes the author can make in scope):

- **VC-1** needs Shane's decision: a recorded per-PR exception, or VR-1 / a reviewed regeneration landing first.
- The release-test failure is main's own.

## 8. Readiness

- **Gate.** D-143 passes on 701e466.
- **Merge.** Merge readiness is still blocked on:
  - merging `origin/main` 4e35c90 (#202, release-policy JSON only, merges cleanly), then rerunning the affected checks and pre-PR on the clean merged tree;
  - VC-1 (Shane's decision);
  - Shane's acceptance of D-143 and of the three changed teammate tests that R0 listed in section 4.3 (they must be listed in the PR).
- If the merge of #202 changes nothing under `apps`, `scripts` or `docs/decisions`, this verdict carries over to the merged tree. Any other change needs a recheck of that delta.
- Live ACRA and real GoldTier readiness are not affected and not claimed.

## 9. Git status

Branch `fix/clear-upload-rejections`, HEAD 701e466, nothing staged. The only change is this untracked report. The reviewer made no implementation, test, configuration or vocabulary edit, and no commit, push, merge, rebase, reset or stash. Its only scratch file is `<scratchpad>/r1-pytest.log`, where `<scratchpad>` = `/private/tmp/claude-501/-Users-tasha-Documents-GitHub-data-dividends-zero-touch-clm/5ffbaee6-1a06-46b4-8369-b5266529d567/scratchpad`.

Verdict: PASS
