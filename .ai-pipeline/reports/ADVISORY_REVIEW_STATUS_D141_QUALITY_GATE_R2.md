# D-141 advisory ownership review display: quality gate R2

Reviewer: an independent Claude Code reviewer subagent. It did not write or fix any of the reviewed content.
Date: 2026-11-17. Scope: bounded change D-141 (PROPOSED; amends the D-121 display only), PR #192. This is the re-review after three merges of `origin/main` into the branch since R1 (`ADVISORY_REVIEW_STATUS_D141_QUALITY_GATE_R1.md`, PASS on 3b75306; R1's reviewed tip was 6d048b3).

## Reviewed content (frozen)

- Worktree `/Users/tasha/Documents/GitHub/dd-clm-advisory-review`, branch `fix/advisory-review-status`, HEAD `d4bebe3f2fa89f745ad62ab1e79e701f614139fb`, tree `6b2ea6becc5a1a6eb1d40566a87140083f1a8882`. The tree was clean at the start of the gate and stayed clean, apart from this untracked report.
- Base: `origin/main` `b8951ee6d5a92d8a1c5bb4cc18bd21d52afa6286`, confirmed after `git fetch origin`. It is an ancestor of HEAD. **Main has not moved** since the author's evidence: `git log HEAD..origin/main` is empty.
- Paths reviewed: all 20 from `git diff --name-only origin/main...HEAD`. These are the 18 code, test and doc paths reviewed in R0 and R1, plus the committed R0 and R1 reports. The sha256 prefix of `git diff origin/main...HEAD -- apps docs` is `3da4e37a57021a25`. The prefix differs from R1's only because the context line numbers moved.
- Merges since R1: ddee1b8 (#191, docs only), 5edb6f5 (#193 to #196: schema 21, revision and nonce writers, ADR-017 dispatch fence, `main.py`, onboarding services) and d4bebe3 (#197 to #200: frontend App and WorkflowManager, mandatory VC-1 in `pre_pr_check.py`, test helpers, docs).

## 1. Executive result

**PASS** for the gate's scope (code, tests, contract, architecture and security). No required fix remains.

**Merge readiness is not granted.** The mandatory VC-1 check in `pre_pr_check.py` fails on d4bebe3. I verified that the failure comes entirely from drift that already exists on `origin/main`. Clearing it is an owner decision, and the gate has no authority over it (section 3). The gate does not treat that exception as granted.

Key facts:

- **D-141 is unchanged by the merges.** The set of added and removed lines in `git diff origin/main...HEAD -- apps docs` is byte-identical to R1's `git diff 49ac458...6d048b3 -- apps docs`. `git diff 6d048b3 HEAD` limited to the branch's own paths touches only `main.py` and `DECISION_LOG.md`, and both changes are main's content. `api_models.py`, `types.ts`, `CaseStatePanels.tsx`, `CaseDetail.tsx`, `stageDisplay.ts`, `design-system.css` and the five assistant modules did not change between 6d048b3 and HEAD.
- **The `main.py` call site is intact and correct.** At `main.py:1483-1490` it passes `ownership=ownership_record` and `ownership_review_advisory=(ownership_record is not None and ownership.review_is_advisory(ownership_record) and not ownership.poc_basis_accepted(ownership_record))`. `ownership_record` comes from `ownership.get(case_id=automation.case_id)` at `main.py:1379`. That is the same composed `OwnershipAnalysisService` instance (`main.py:814`) and the same record that is passed to `from_domain(ownership=...)`.
- **The projection still ties the flag to readiness.** At `api_models.py:2742-2749` it requires `readiness_status(...) == "COMPLETE"` and `clm.readiness.ownership.reference_id == str(ownership.analysis_id)`.
- **No interaction with the merged code.** Schema 21, the revision and nonce writers and the ADR-017 fence add no ownership or readiness logic. A grep of the merge delta under `apps/backend/app` for ownership, readiness or advisory finds only the schema-20 legacy envelope class. `review_is_advisory` and `poc_basis_accepted` (`ownership_analysis.py:1334-1360`) are unchanged. `advisory_review` is a read-time projection and is never persisted, so the schema-21 snapshot and migrations cannot carry or drop it.

## 2. Acceptance checklist

| # | Requirement | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Backend `advisory_review` is optional, None by default, and appears only on OWNERSHIP_UBO | Met | `api_models.py:1455`, `2742-2749`. The lines are identical to R1. |
| 2 | True only when the node is COMPLETE, the readiness reference_id is the current analysis_id, `review_is_advisory` holds and `poc_basis_accepted` does not | Met | `api_models.py:2742-2749`, `main.py:1379,1483-1490`. The reviewer's run of `test_advisory_review_node_flag.py` passes at d4bebe3 (HTTP-level and projection tests). |
| 3 | No change to status, readiness, D-121/D-124, the audit code or blocking mode | Met | The branch diff contains no service, readiness or audit code. The D-124 suite and the ADR-017 fence and reader suites pass (section 4). |
| 4 | Frontend shows amber "Review advised" with words in the chip, rail and tile, plus the subtitle, and green only without an open review | Met | The frontend files are unchanged since R1. The reviewer's run of `CaseStatePanels.test.tsx` gives 69/69. The author's d4bebe3 tsc, build, vitest and affected E2E 10/10 are matched to this HEAD. |
| 5 | Assistant shows the "review advised" step and REVIEW_ADVISED readiness, offers one catalog line in that state, and the copilot drops completion claims unless ownership is READY | Met | The assistant modules are unchanged since R1. The reviewer's runs of `test_advisory_review`, `test_copilot`, `test_claims` and `test_guardrails` all pass. |
| 6 | Verification claims stay with the authority check | Met | Unchanged since R1. |
| 7 | No existing assertion changed or removed, and no teammate test edited | Verified | The branch-only diff equals R1's diff. The merges brought main's test changes and none of the branch's. |
| 8 | Decision recorded | Met | D-141 is at `DECISION_LOG.md:2983`, after D-140 and the SF-002 amendment. The #193-#196 merge inserted D-135 earlier in the file with no conflict. Neither `origin/main` nor any other open PR uses D-141. |
| 9 | Mandatory pre-PR vocabulary check (VC-1) | **Not met. Owner decision outside the gate's authority.** | Section 3. |

## 3. Contract and integration findings

- **No contract findings.** The API addition stays optional and is mirrored in `types.ts`. Evidence class is Mock; nothing claims Live.
- **VC-1 (owner decision; it does not affect the gate verdict, but it does block merge readiness).**
  - **Status.** The reviewer ran `scripts/check_boundary_vocabulary.py` at d4bebe3. It returns `FAIL_CHANGED_NOT_CURRENT` with `file_word_delta` code +1, conversation +1 and `head_drift` code_vocabulary +77/-2.
  - **#192's own delta.** `git diff origin/main...HEAD -- synthetic_boundary.json` adds exactly two words: `advised` (conversation_vocabulary) and `verdict` (code_vocabulary). Nothing is removed.
  - **D-094 review of the two words.** Both are ordinary English words. Neither is a real-person or real-company name, and neither is shaped like a credential, an identifier or PII. Their sources are in the branch:
    - `advised` comes from the "Review advised" wording and the new catalog line.
    - `verdict` comes from the docstring "the caller's verdict" in `api_models.py`.
    - Both are synthetic-boundary content and acceptable.
  - **The drift is all main's (independently verified).**
    - **Fresh export.** I made my own `git archive origin/main` export at `<scratchpad>/r2/main-export`. I did not use the author's export.
    - **Same drift on both trees.** I ran a copy of the author's `vocab_diff.py` (read first; it only diffs generated against stored) with `python -I` against the export and against the worktree. The outputs are byte-identical: `/code_vocabulary ADDED 77 [...] REMOVED ['inserts', 'treats']`. This means the stored file at HEAD holds `advised` and `verdict` in sync with the generator, and the whole remaining staleness is main's.
    - **The builder fails on both.** `build_synthetic_boundary.py --check` exits 1 on both the export and HEAD.
    - **The test fails on both.** `test_the_boundary_file_is_current` fails at HEAD, and the author reports it also fails on the export.
  - **Why VC-1 fails rather than warns.** `classify()` (`check_boundary_vocabulary.py:118-132`) returns `PRE_EXISTING_DRIFT` only when the file is untouched. #192 must edit the file, so it fails.
  - **No in-scope fix exists.**
    - If the branch dropped its edit, its two words would become `FAIL_NEW_DRIFT`.
    - Rewording could remove `verdict`, but not `advised`, which is the feature's own wording.
    - Regenerating would pull main's +77/-2 into this PR. #198's body (`gh pr view 198`) assigns that reconciliation to the separate owner gate VR-1, which "runs after D-141 and D-142 land".
  - **What clears it.** One of these, decided by Shane:
    - a recorded per-PR exception;
    - VR-1 (or a regeneration with an independent review of the full word delta) lands first, then main is merged and VC-1 is rerun.
- **Owner dependency (unchanged).** D-141, including the catalog line `OWNERSHIP_REVIEW_ADVISED`, needs Shane's acceptance.
- **Coordination note (unchanged from R1).** The unpushed local branch `fix/clear-upload-rejections` also uses D-141. Whichever branch merges second renumbers.

## 4. Tester and adversarial findings

Environment: the worktree-only venv `.../scratchpad/venv-advisory/bin/python`. `import app` resolves to `/Users/tasha/Documents/GitHub/dd-clm-advisory-review/apps/backend/app/__init__.py` and `import ai_assistant` resolves to the worktree. The repo-root `.venv` was not used.

Reviewer runs at d4bebe3:

- **Backend.** I ran `pytest tests/test_advisory_review_node_flag.py tests/test_d124_advisory_continuation.py tests/test_adr017_dispatch_fence.py tests/test_adr017_reader_release.py`: **119 passed, 0 failed**. This covers the D-141 flag over HTTP and in the projection, D-124 advisory continuation, and the new fence and reader paths together.
- **Assistant (one file per process).**

  | File | Result |
  | --- | --- |
  | `test_advisory_review` | 8 passed |
  | `test_copilot` | 134 passed |
  | `test_claims` | 101 passed |
  | `test_guardrails` | 4 passed |
  | `test_remote_test` | 67 passed, **1 failed** (`test_the_boundary_file_is_current`, the VC-1 drift above) |
- **Frontend.** `vitest run src/pages/CaseStatePanels.test.tsx`: 69/69.
- **Static checks.** `ruff check` on the eight changed Python files: all passed. `mypy` on `app/main.py` and `app/api_models.py` (backend) and on the five assistant modules: no issues.
- **Whitespace.** `git diff --check origin/main...HEAD` is clean, and so is `git diff --check 6d048b3 HEAD`.

Author evidence on d4bebe3, checked against this HEAD:

- **Backend full suite.** The log has no summary line (`-q` twice). Counting the progress characters gives exactly 4168 `.`, 207 `s` and 7 `F`. The 7 failures are the known macOS-only ones (6 × `test_s2_local_ocr` fonts, plus `test_a_real_child_process_sees_no_backend_secret`), which also fail on main.
- **Assistant per-file.** 86 files. The only failure is `test_remote_test.py::test_the_boundary_file_is_current`.
- **Frontend.** tsc EXIT=0 and build EXIT=0. Vitest: 1581 passed, plus the known macOS-only `ViteHistoryFallback` failure.
- **Affected E2E.** `scripts/run_e2e.py --selectors-file`: status PASS, complete, 10/10 in isolated lifecycles, with the D-141 spec and the ownership and partnership journeys. The run used the frozen tree after commit time.
- **Pre-PR.** The log records HEAD d4bebe3 and origin/main b8951ee, a clean tree, `SUMMARY: FAIL (1 unsafe condition, 2 warnings)`. The unsafe condition is VC-1 and the warnings are the expected hotspot and API-file warnings.

Not run by the reviewer: the full E2E suite (not required), physical Mongo (D-141 adds no persistence; schema 21 is main's own and covered by main's gates), and the full backend and frontend suites (the author's evidence is matched to this HEAD and the D-141 delta is unchanged). All evidence is local; CI is billing-blocked and nothing here is hosted CI.

## 5. Code and architecture review

- **No new findings.** The merges did not touch D-141 logic. The `main.py` call site still sits inside the case-detail handler, next to the other uses of `ownership_record`. The merged changes nearby (`_case_is_sent`, `_build_dispatch_fence`, the removed `target-confirmation` route, recovery-only Submit and the reconfirmation refusal in `_refusing_unsendable_case`) are independent of the projection.
- **No semantic conflict** with #193-#200:
  - #197 changes `App.tsx`, `WorkflowManager.tsx` and `workflowApi.ts`, not the case-state panels or stage display.
  - The assistant changes from main are only deploy, egress docs and an egress test.
- R0's non-required notes still apply and remain optional:
  - The frontend `isAdvisoryReview` does not check `COMPLETE`.
  - `briefing.ownership_advised` duplicates the guardrails helper.

## 6. Security review

There are no findings. The flag is a boolean with no PII. It is projected only by the existing authorised GET. The exact-line catalog gains one conditional line, unchanged since R1. No guardrail, authority check, maker-checker, permission recheck or fence control is relaxed. The two new vocabulary words pass the D-094 criteria (section 3).

## 7. Required fixes

None within the gate's scope.

Outside the gate's authority and not a fix the author can make in scope: **VC-1 needs Shane's decision** (section 3). Until he decides, pre-PR is FAIL and #192 is not merge-ready.

## 8. Readiness

- **Gate.** D-141 passes the gate on d4bebe3.
- **Merge.** Merge readiness is blocked on two owner decisions:
  - VC-1 (a per-PR exception, or VR-1 first);
  - acceptance of D-141 and its catalog line.
- Live ACRA and real GoldTier readiness are not affected and not claimed.

## 9. Git status

Branch `fix/advisory-review-status`, HEAD d4bebe3, nothing staged. The only change is this untracked report. The reviewer made no implementation, test, configuration or vocabulary edit, and no commit, push, merge, rebase, reset or stash. The reviewer's scratch files are only under `<scratchpad>/r2/`.

Verdict: PASS
