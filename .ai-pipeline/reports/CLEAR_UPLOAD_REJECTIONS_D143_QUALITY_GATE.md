# D-143 clear upload rejection reasons: quality gate R0

Reviewer: an independent Claude Code reviewer subagent. It did not write or fix any of the reviewed content.
Date: 2026-11-17. Scope: bounded change D-143 (PROPOSED; drafted as D-140, then D-141), "Specific, plain reasons when an upload fails the local document checks" (R1 to R4). Round R0. Method: `.agents/skills/fyp-quality-gate/SKILL.md` read directly (the user authorised this instead of the Skill tool).

## Reviewed content (frozen)

- Worktree `/Users/tasha/Documents/GitHub/dd-clm-clear-upload-rejections`, branch `fix/clear-upload-rejections`, HEAD `98e96f05389d2986763a513251565e0d5d9d20d3`, tree `1d9f28f453df239010e92d34d32137c0c893b862`. The tree was clean at the start and stayed clean, apart from this untracked report.
- Base: `origin/main` `e73c85d1434b3e62b66b88c21b6d4c8eaef8a0d5`, confirmed after `git fetch origin`. It is an ancestor of HEAD. **Main has not moved**: `git log HEAD..origin/main` is empty.
- Paths reviewed: all 18 from `git diff --name-only origin/main...HEAD`:
  - backend app: `connectors/idp.py`, `connectors/local_document_runtime.py`, `connectors/local_document_worker.py`, `connectors/local_process.py`, `services/document_errors.py`, `services/document_media.py`, `services/document_processing.py`;
  - backend tests: new `test_upload_rejection_reasons.py`; changed teammate tests `test_sf001_sf002_document_worker_hardening.py`, `test_s2_local_ocr.py`, `test_pre_phase12_workspace_multidoc.py`;
  - frontend: `src/App.tsx`, `src/pages/CaseDetail.tsx`, new `src/uploadRejection.ts`, new `src/pages/UploadRejectionBanner.test.tsx`, new `e2e/upload-rejection.e2e.ts`;
  - `apps/assistant/ai_assistant/synthetic_boundary.json`; `docs/decisions/DECISION_LOG.md`.
- Branch commits: 5370e3d (feature), ce0d9c2 and 5805801 (main merges; 5805801 renumbers to D-143), 3dad3ba (bomb.png expectation), 4f19691 (Technical details after the actions), 98e96f0 (merge of #201). `git diff 4f19691 98e96f0 -- apps scripts` is empty, confirmed.

## 1. Executive result

**PASS WITH MINOR FIXES** for the gate's scope (code, tests, contract, architecture and security). One bounded hygiene fix is required (F1, line endings in `App.tsx`). No security, contract or false-success defect was found.

**Merge readiness is not granted.** The mandatory VC-1 check fails. I verified that the remaining drift is all main's. Clearing it is an owner decision outside the gate's authority (section 3). The gate does not treat that exception as granted.

Key facts:

- **Every limit is unchanged.** I ran the worker as a child process on the same ten boundary and hostile inputs against HEAD and against a fresh `git archive origin/main` export. The accept/reject set is identical. Only the exit code of a rejection changes (main: always 2; HEAD: 10 to 14 for the five fixed reasons, 2 otherwise). The 8000x2000 PNG (exactly 16,000,000 px) and the 10-frame TIFF are accepted on both. The 4001x4001 PNG, the 8000x2001 PNG, the 11-frame TIFF, the 11-page PDF, the encrypted PDF, the `/F` filespec PDF and garbage PDF/PNG are rejected on both. Stdout was empty and stderr was empty on every rejection.
- **Only fixed exit codes leave the child.** `_Rejection` carries one of five fixed keys. `main()` returns `REJECTION_EXIT_CODES[reason]` and any other exception still returns `EXIT_MALFORMED = 2`. stderr stays `DEVNULL` in `run_bounded_process`. No document text, name, object id or library text reaches the parent.
- **Unknown exit codes stay generic.** `run_bounded_process` maps only the five listed codes. Exit 1, 2, 7 and a signal (negative) map to `DOCUMENT_STRUCTURE_INVALID` (new test, which I ran). `LocalDocumentProcessingError` still allow-lists codes and maps anything else to `IDP_PROCESSING_FAILED`.
- **SF-001 and SF-002 are unchanged.** `Image.open(..., formats=[expected])` and the decoded-format check are only re-indented into a `try`. `_limit_memory()`, `MAX_WORKER_ADDRESS_SPACE` and the #190 macOS/Windows skip are untouched. `child_environment()` is unchanged.
- **No new retry or replace path.** "Choose a different file" calls the existing `pendingDocuments.onDiscard()` and then focuses the existing `#case-document-upload` file input. It is offered only when every failed file was refused before storage with a file-content code. Stored failed documents, timeouts, runtime-unavailable and network failures keep "Try upload again".

## 2. Acceptance checklist

| # | Requirement | Result | Evidence |
| --- | --- | --- | --- |
| 1 | R1: the worker reports a rejection only as fixed exit codes 10 to 14; everything else stays 2; codes 0, 1, 2 and negatives are not reused | Met | `local_document_worker.py` diff; reviewer probe (section 4); `test_worker_and_runtime_exit_code_maps_agree_and_avoid_reserved_codes` |
| 2 | R1: every page, size, pixel, text and active-content limit unchanged | Met | Constants untouched; the HEAD/main probe gives identical accept/reject sets; the split checks (`_dimensions`, `_safe_pdf`, frame bounds) keep every old reject branch |
| 3 | R2: runtime maps to the five API codes; unmapped exits fall back to `DOCUMENT_STRUCTURE_INVALID`; `DOCUMENT_TOO_LARGE` not reused | Met | `local_document_runtime.DOCUMENT_REJECTION_CODES`, `local_process.py`, `idp.py` allow-list; `test_unmapped_exit_codes_fall_back_to_structure_invalid`, `test_specific_codes_survive_the_processing_error_allowlist` |
| 4 | R3: one backend wording table, plain message with a next step; timeout and runtime-unavailable keep their codes | Met | `document_errors.py`; `document_media.py` and `document_processing.py` read the same table; HTTP tests assert `{code, message}` exactly, and that the file name, a secret marker, library words and the URI never appear in the body |
| 5 | R4: banner shows the plain message; case ID, retry wording and code in collapsed Technical details placed after the actions; "Choose a different file" only for pre-storage file-content rejections | Met | `CaseDetail.tsx`, `uploadRejection.ts`, `App.tsx`; `UploadRejectionBanner.test.tsx` 13/13; E2E `upload-rejection.e2e.ts` (3 tests) |
| 6 | Stale rejection cannot attach to a newer error | Met | `rejection` is passed only when `uploadRejection.forMessage === requestError`; reset clears it |
| 7 | Teammate keyboard-focus test unchanged | Met | `responsive-layout.e2e.ts` is not in the branch diff; `:477` PASS in the author's E2E on 4f19691 |
| 8 | Changed teammate tests listed and justified | Met | Section 4.3: all three are justified consequences of D-143, none weakened |
| 9 | Decision recorded with a free number | Met | D-143 at the end of `DECISION_LOG.md`; not used on `origin/main` (highest there is D-141; D-142 reserved in `DEVELOPMENT_WORKFLOW.md:208`); the only other open PR (#187) does not use it |
| 10 | Diff hygiene | **Minor fix (F1)** | `git diff --check origin/main...HEAD` is clean, but `App.tsx` line endings were normalised (section 5) |
| 11 | Mandatory pre-PR vocabulary check (VC-1) | **Not met. Owner decision outside the gate's authority.** | Section 3 |

## 3. Contract and integration findings

- **API contract.** The five new codes are additive values of the existing `detail.code` string on the existing 422 response. `DOCUMENT_STRUCTURE_INVALID` keeps its code and gets new wording. Timeout and runtime-unavailable keep their codes. Evidence class stays Mock/local; nothing claims Live.
- **Coupling.** The parent keeps its own copy of the exit-code map so it never imports the native libraries. The new test pins the two maps against each other. Acceptable.
- **VC-1 (owner decision; it does not change the gate verdict, but it blocks merge readiness).**
  - **Status.** I ran `scripts/check_boundary_vocabulary.py` at 98e96f0: `FAIL_CHANGED_NOT_CURRENT`, `file_word_delta` code_vocabulary +7/-1, `head_drift` code_vocabulary +77/-2. The author's `up-pre-pr.log` on 98e96f0 (origin/main e73c85d) shows the same: `SUMMARY: FAIL (1 unsafe condition(s), 1 warning(s))`, the warning being the `App.tsx` hotspot.
  - **The drift is all main's (independently verified).** I made my own fresh `git archive origin/main` export at `<scratchpad>/qg-d143/main-export` and ran a copy of `vocab_diff.py` (read first; it only diffs the generated vocabulary against the stored file) with `python -I` on the export and on the worktree. The two outputs are identical apart from the root path: `/code_vocabulary ADDED 77 [...] REMOVED ['inserts', 'treats']`. So the stored file at HEAD is in sync with this branch's own changes, and the whole remaining staleness is main's (#195/#196). `tests/test_remote_test.py::test_the_boundary_file_is_current` fails at HEAD (67 passed, 1 failed), consistent with that.
  - **The branch's 8-word delta** (`git diff origin/main HEAD -- synthetic_boundary.json`):
    - added `encrypted` (worker reason key), `export`, `happening`, `interactive`, `print`, `simpler`, `uploading` (the new `document_errors.py` wording; `print` was already used elsewhere in the backend but is new to the stored code vocabulary through these strings);
    - removed `pixels`: on main it came only from the worker's string literals `ValueError("document pixels")`, which became `_Rejection("CONTENT_TOO_LARGE")`. Correct removal.
  - **D-094 review.** All eight are ordinary English words. None is a real person's or company's name, and none is shaped like a credential, identifier or PII. They are synthetic-boundary content and acceptable.
  - **No in-scope fix.** Dropping the edit would turn the branch's own words into new drift. Regenerating would pull main's +77/-2 into this PR, which #198 assigns to the owner's VR-1 ("runs after D-141 and D-142 land").
  - **What clears it.** Shane decides: a recorded per-PR exception, or VR-1 (or a regeneration with an independent review of the full word delta) lands first, then main is merged and VC-1 rerun.
- **Release test (main's, not this branch's).** `tests/release/test_source_images_render.py::test_backend_schema_version_is_read_from_the_commit` fails at HEAD (`assert 21 == 20`). `git diff origin/main HEAD -- tests/release tools apps/backend/app/models.py` is empty, and calling the same `backend_snapshot_schema` for commit e73c85d (origin/main) returns 21. Main's own test therefore fails on main since #195 (schema 21). Not caused by this branch.
- **Owner dependencies.** D-143 needs Shane's acceptance. The three changed teammate tests (section 4.3) must be listed in the PR for Shane.

## 4. Tester and adversarial findings

Environment: the worktree-only venv `<scratchpad>/venv-upload/bin/python`. `import app` and `import ai_assistant` resolve to this worktree. The repo-root `.venv` was not used. Caches went to the scratchpad or were disabled (`-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`, `MYPY_CACHE_DIR`, `vite build --outDir <scratchpad>`).

### 4.1 Reviewer runs at 98e96f0

- **Backend targeted.** `pytest tests/test_upload_rejection_reasons.py tests/test_sf001_sf002_document_worker_hardening.py tests/test_pre_phase12_workspace_multidoc.py tests/test_s2_local_ocr.py`: **100 passed, 1 skipped, 7 failed**. All 7 are the known macOS-only failures that also fail on main (6 × `test_real_local_ocr_acceptance` font `OSError: cannot open resource`, plus `test_a_real_child_process_sees_no_backend_secret`). All five `test_malformed_synthetic_images_fail_closed` cases pass, including bomb.png within the 25 s bound.
- **Adversarial worker probe** (child process, `validate`, HEAD vs a fresh main export):

  | Input | main exit | HEAD exit |
  | --- | --- | --- |
  | PNG 4001x4001 (Pillow warning band, escalated to error) | 2 | 13 |
  | PNG 8000x2001 (>16M px) | 2 | 13 |
  | PNG 8000x2000 (=16M px, at the limit) | 0 | 0 |
  | TIFF 10 frames | 0 | 0 |
  | TIFF 11 frames | 2 | 10 |
  | PDF 11 pages | 2 | 10 |
  | PDF encrypted, 11 pages | 2 | 11 |
  | PDF with a `/F` filespec | 2 | 12 |
  | garbage PDF / garbage PNG / bad argv | 2 | 2 |

  Stdout and stderr were empty on every rejection in both trees.
- **Assistant.** `tests/test_remote_test.py` (one process): 67 passed, 1 failed (`test_the_boundary_file_is_current`, VC-1 above).
- **Frontend.** `tsc -b` EXIT 0; `vite build` EXIT 0 (output in the scratchpad). Full `vitest run --maxWorkers=2`: **1594 passed, 1 failed** (`ViteHistoryFallback`, the known macOS-only failure). Focused: `UploadRejectionBanner`, `PendingDocumentsBanner`, `S1FormsSession`, `UiV2Integration`: 66/66.
- **Static checks.** `ruff check` on the 11 changed Python files: all passed. `mypy` on the 7 changed backend app modules: no issues.
- **Whitespace.** `git diff --check origin/main...HEAD` is clean; the report file was checked separately.

### 4.2 Author evidence, matched to this HEAD

- **Frontend.** The author's `up-frontend*.log` are on 3dad3ba, before 4f19691 changed `CaseDetail.tsx`; the reviewer's own tsc, build and full vitest above replace them for HEAD.
- **Backend full suite** (`up-backend.log`, 5805801): 4189 passed, 8 failed, 207 skipped. The 8th failure was bomb.png, fixed in 3dad3ba; the only backend change since 5805801 is that test line (`git diff 5805801 98e96f0 -- apps scripts` = that test + `CaseDetail.tsx`), and my rerun covers it.
- **Assistant per-file** (`up-assistant.tsv`, 3dad3ba): I re-tallied 86 files, 4311 passed, 1 failed (`test_the_boundary_file_is_current`), 0 errors. `apps/assistant` is unchanged since then.
- **Affected E2E** (`up-e2e.json`): identity head 4f19691, tree `f1c195f…` (matches `git rev-parse 4f19691^{tree}`), not dirty, origin_main e73c85d; status PASS, complete, 12/12 isolated lifecycles, `keep_going: false`. The `upload-rejection` selectors (`:108/:149/:169`) are Playwright-reported lines; the log shows each ran `[1/1]` with the expected test title. `4f19691..98e96f0` changes nothing under `apps` or `scripts`, so the run carries over.
- **Pre-PR** (`up-pre-pr.log`, 98e96f0): FAIL only on VC-1, plus the hotspot warning.

Not run by the reviewer: the full E2E suite (not required), the full backend suite (reused as above), physical Mongo (D-143 adds no persistence). All evidence is local; CI is billing-blocked and nothing here is hosted CI.

### 4.3 Changed teammate tests (for Shane)

| Test (owner) | Change | Judgement |
| --- | --- | --- |
| `test_sf001_sf002_document_worker_hardening.py::test_malformed_synthetic_images_fail_closed` (Shane, #188/#190) | bomb.png (IHDR claims 60000x60000) now expects `DOCUMENT_PAGE_TOO_LARGE`; the other four cases still expect `DOCUMENT_STRUCTURE_INVALID`; the 25 s bound is unchanged | **Justified, not weakened.** The input is still rejected, still fail-closed, still inside the time bound. The assertion stays exact (one specific code per case). Pillow raises `DecompressionBombError` before decoding, because the declared size is over `MAX_IMAGE_PIXELS = MAX_PAGE_PIXELS`; "a page is too large" is truthful about the declared size. |
| `test_s2_local_ocr.py` (Shane, #69): image dimension and TIFF frame limits, PDF pages/encrypted/script/remote, image pixel and PDF aggregate pixel limits | Each `DOCUMENT_STRUCTURE_INVALID` expectation becomes the specific code (`PAGE_TOO_LARGE`, `TOO_MANY_PAGES`, `ENCRYPTED`, `ACTIVE_CONTENT` ×2, `PAGE_TOO_LARGE`, `CONTENT_TOO_LARGE`) | **Justified, and stricter.** Same inputs, same rejection; the expected code is narrower than before. The text-limit case is not in this file; it is covered by the new `test_text_limit_is_checked_at_extraction_with_its_own_code`. |
| `test_pre_phase12_workspace_multidoc.py::test_fake_marker_only_pdf_is_a_bounded_client_error_not_503` (Shane, #69) | The expected message for `DOCUMENT_STRUCTURE_INVALID` becomes "This file isn't a readable PDF or image. Re-export it and upload it again." | **Justified, not weakened.** The code, the not-503 assertion and the exact-equality check are unchanged; only the R3 wording changes. The file's CRLF line endings are preserved (827 CRLF lines before and after). |

## 5. Code and architecture review

- **F1 (Low; required minor fix): `App.tsx` line endings normalised.** `origin/main`'s `App.tsx` has mixed endings (2316 of its lines end in CRLF). After 5370e3d every line ends in CRLF (2451 of 2451), so about 120 untouched LF lines were rewritten to CRLF. `git diff origin/main...HEAD --stat` shows 135+/120- for this file, while `git diff --ignore-cr-at-eol` shows only the real change of 15 inserted lines. Hunks that differ only by line ending include the AI assistant and workflow imports and lines in `validateIntakeFiles` and `isRegistryIntakeUnavailable`. `App.tsx` is the integration hotspot flagged by pre-PR, so the churn inflates the review diff and raises the merge-conflict risk for teammates. **Fix:** restore each untouched line's original ending so that `git diff origin/main...HEAD -- apps/frontend/src/App.tsx` shows only the 15 real insertions (for example, re-apply the 15 lines onto main's bytes). No behaviour change; recheck = that file's diff, `tsc`, and the focused vitest files.
- **N1 (informational, optional).** `DOCUMENT_STRUCTURE_INVALID` also covers non-file causes: an interpreter crash (exit 1), a signal, a Linux `RLIMIT_AS` `MemoryError` (exit 2) or worker output that fails the parent's checks. Those now say "This file isn't a readable PDF or image" and offer "Choose a different file". This code mapping existed before; the new wording only makes the cause sound more certain. For the memory cap, resending the same file would fail again, so the action is still right. A later change could add a separate runtime code. Not required for D-143.
- **N2 (informational).** `document_media.py` keeps the old "bounded local structure checks" sentence for codes outside the table (`DOCUMENT_OUTPUT_LIMIT_EXCEEDED`, OCR codes). This is consistent with R3's scope.
- **Correctness details checked.** The split of `_safe_pdf` checks encryption before reading the page count, so it no longer depends on `len(reader.pages)` for an encrypted file. A non-TIFF image with more than 10 frames still fails as malformed before the page rule. `_Rejection` raised inside the new `try` is not swallowed by the bomb `except`. `rejectedBeforeStorage` is false whenever the key has a stored failed document, so the existing retry flow is kept.
- **Scope.** No scope creep beyond R1 to R4 and their tests, apart from the line endings in F1.

## 6. Security review

There are no security findings.

- The child-to-parent channel carries only an integer from a fixed set; stderr is discarded; the parent builds every message from a fixed table.
- The HTTP tests check that the response body contains no file name, no secret marker from the encryption password or link URI, and no library words.
- The banner shows the RM's own file name as React text (escaped) next to the backend's fixed message.
- SF-001 (single decoder plugin, minimal child environment) and SF-002 (address-space cap, #190 platform rule) are unchanged; no limit was relaxed.
- No authentication, permission or maker-checker path is touched.
- The 8 vocabulary words pass D-094 (section 3).

## 7. Required fixes

1. **F1:** restore the original line endings of the untouched lines in `apps/frontend/src/App.tsx`, so that the branch diff for that file shows only the 15 inserted lines. Bounded, no behaviour change. The recheck reviews only that delta (file diff, `tsc`, focused vitest).

Outside the gate's authority and not a fix the author can make in scope: **VC-1 needs Shane's decision** (section 3). Until he decides, pre-PR is FAIL and the branch is not merge-ready.

## 8. Readiness

- **Gate.** D-143 passes with one minor fix (F1) on 98e96f0.
- **Merge.** Merge readiness is blocked on:
  - F1 and its recheck;
  - VC-1 (a per-PR exception, or VR-1 first);
  - Shane's acceptance of D-143 and of the three listed teammate-test changes.
- Live ACRA and real GoldTier readiness are not affected and not claimed.

## 9. Git status

Branch `fix/clear-upload-rejections`, HEAD 98e96f0, nothing staged. The only change is this untracked report. The reviewer made no implementation, test, configuration or vocabulary edit, and no commit, push, merge, rebase, reset or stash. Scratch files are only under `<scratchpad>/qg-d143/` (`<scratchpad>` = `/private/tmp/claude-501/-Users-tasha-Documents-GitHub-data-dividends-zero-touch-clm/5ffbaee6-1a06-46b4-8369-b5266529d567/scratchpad`).

Verdict: PASS WITH MINOR FIXES
