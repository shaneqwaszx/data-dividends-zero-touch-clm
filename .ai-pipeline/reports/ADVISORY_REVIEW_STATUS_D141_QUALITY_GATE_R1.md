# D-141 advisory ownership review display: quality gate R1

Reviewer: an independent Claude Code reviewer subagent. It did not write or fix any of the reviewed content.
Date: 2026-11-16. Scope: bounded change D-141 (PROPOSED; amends the D-121 display only). This is the recheck after R0 (`ADVISORY_REVIEW_STATUS_D141_QUALITY_GATE.md`, PASS WITH MINOR FIXES on e34a5a7).

## Reviewed content (frozen)

- Worktree `/Users/tasha/Documents/GitHub/dd-clm-advisory-review`, branch `fix/advisory-review-status`, HEAD `3b7530673338be980aeb542ff2d51879fe054cff`, tree `865e49e2dc709cf62035aa1244a1a21f526e8114`.
- Base: `origin/main` `49ac458a07dd412863cef68db1fc56057902b0e0`. I confirmed this after `git fetch`. It is an ancestor of HEAD.
- Paths reviewed: all 19 from `git diff --name-status 49ac458 HEAD`. These are the 18 code, test and doc paths R0 reviewed, plus the committed R0 report. The sha256 prefix of the diff for `apps/` and `docs/` is `6f3b5e532671e5e3`.
- R0 to R1 delta (commit 3b75306): `apps/assistant/ai_assistant/claims.py` (`_OWNERSHIP_DONE`, +2/-1), `apps/assistant/tests/test_advisory_review.py` (`CLAIMS` gains 2 entries), and the R0 report.
- The tree was clean at the start of the gate. The only write is this untracked report.

## 1. Executive result

**PASS.** The R0 fix is correct and complete. `_OWNERSHIP_DONE` now allows `now/already/fully/all` between `has/have` and `been`, and keeps the adverbs after the auxiliary. Both sentences R0 named are dropped as `unsupported_status` on an advisory case and kept on a confirmed case.

Over-matching was probed:

- Negated sentences are kept: "has not been", "has not yet been", "hasn't been", "has never been" and "has yet to be".
- Conditional sentences are kept: "Once…", "When…" and "If… has already been completed".
- The catalog line passes in both modes.
- A READY case without the flag is unaffected.

I re-reviewed the whole branch diff and found no new defect. No safety control is weakened: the copilot rule only adds a drop, the catalog gains one line that is offered only in its condition, and authority, maker-checker, permission rechecks and RBAC are unchanged.

## 2. Acceptance checklist

| # | Requirement | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Backend `advisory_review` is optional, None by default, and appears only on OWNERSHIP_UBO | Met | `api_models.py:1455`, `2742-2749`. Unchanged since R0. |
| 2 | True only when the node is COMPLETE, the readiness reference_id is the current analysis_id, `review_is_advisory` holds and `poc_basis_accepted` does not | Met | `api_models.py:2742-2749`, `main.py:1406-1413`. R0 backend evidence is still valid because 3b75306 touches no backend file. |
| 3 | No change to status, readiness, D-121/D-124, the audit code or blocking mode | Met | The diff contains no service, readiness or audit code. D-141 A5. |
| 4 | Frontend shows amber "Review advised" with words in the chip, rail and tile, plus the subtitle, and green only without an open review | Met | `stageDisplay.ts:110-120`, `CaseStatePanels.tsx`, `CaseDetail.tsx:1342-1346`. The R0 vitest and E2E evidence (e34a5a7) is still valid because 3b75306 touches no frontend file. |
| 5 | Assistant shows the "review advised" step and REVIEW_ADVISED readiness (in `_OWNERSHIP_INCOMPLETE`), offers one catalog line in that state, and the copilot drops completion claims unless ownership is READY | Met (R0 M1 closed) | `context.py:102-123,348-352`, `guardrails.py:123-163,324-325`, `guide.py:251-259`, `claims.py:533-538,711-714`. Reviewer probes are in section 4. |
| 6 | Verification claims stay with the authority check | Met | `_OWNERSHIP_DONE` contains no `verified`/`settled`. The R0 probe "Ownership is verified." gives `authority_claim`. |
| 7 | No existing assertion changed or removed, and no teammate test edited | Verified | Across `49ac458..HEAD`, the only removed test line is the vitest import line (`vi` added). In 3b75306, the `CLAIMS` tuple keeps its three original entries and appends two. `test_copilot.py` and `test_claims.py` are not in the diff. |
| 8 | Decision recorded | Met | `DECISION_LOG.md` D-141 A1-A5 (PROPOSED). The A4 wording is now accurate. |

## 3. Contract and integration findings

- **No findings.** The API addition is optional and mirrored in `types.ts`. Evidence class is Mock; nothing claims Live.
- Owner dependency, kept apart from code readiness: D-141, including the new catalog line `OWNERSHIP_REVIEW_ADVISED`, needs Shane's acceptance.
- **Coordination note (not a defect in this candidate):** the unpushed local branch `fix/clear-upload-rejections` also uses `## D-141` ("Specific, plain reasons when an upload fails the local document checks"). Neither `origin/main` (latest is D-140) nor any open PR holds D-141. Whichever branch merges second must renumber its decision and its code comments.

## 4. Tester and adversarial findings

Environment: the worktree-only venv `.../scratchpad/venv-advisory/bin/python`. `import app` resolves to `/Users/tasha/Documents/GitHub/dd-clm-advisory-review/apps/backend/app/__init__.py` and `import ai_assistant` resolves to `.../dd-clm-advisory-review/apps/assistant/ai_assistant/__init__.py`.

Reviewer runs at 3b75306, run one after another:
- `pytest tests/test_advisory_review.py tests/test_copilot.py tests/test_claims.py tests/test_guardrails.py` gives **247 passed, 0 failed** (log `scratchpad/r1-assistant-targeted.log`).
- `scripts/build_synthetic_boundary.py --check` reports "synthetic boundary is current".
- `ruff check` on `claims.py` and `test_advisory_review.py` gives "All checks passed!". `mypy ai_assistant/claims.py` reports no issues.
- `git diff --check 49ac458 HEAD` is clean.

Regex probes (`scratchpad/r1_probe.py`): each sentence was run through `copilot.check_answer` on the advisory facts (ADVISED) and the confirmed facts (CONFIRMED) from the new test.

- **Dropped on ADVISED (`unsupported_status`) and kept on CONFIRMED:**
  - "The UBO check has now been completed."
  - "Ownership has already been completed."
  - "Ownership has been completed."
  - "The UBOs have all been cleared."
  - "Ownership has fully been resolved."
  - "Ownership has now been fully completed."
  - "Beneficial ownership has already been sorted."
  - "Ownership and UBO have now been completed."
- **Kept on ADVISED:**
  - Negated: "Ownership has not been completed.", "…has not yet been…", "…hasn't been…", "…has never been…", "The UBO check has yet to be completed.", "Ownership is not verified yet."
  - Conditional: "Once ownership has been completed, you can continue.", "When the UBO check has now been completed, …", "If ownership has already been completed, …"
  - Non-completion verbs: "Ownership has been advised for review.", "Ownership has been reviewed by nobody."
  - The catalog line itself.
- "The ownership review has been done." is dropped on both ADVISED and CONFIRMED. On CONFIRMED the new rule cannot fire (ownership READY), so an existing rule drops it against the fixture's open items. That behaviour predates this change.
- Hedged "Ownership may have been completed." is dropped on ADVISED. The R0 pattern (`have been`) already did this. It fails closed and is acceptable, because an advisory case should not suggest completion.
- Remaining small under-match forms that R0 marked as lower value ("Ownership: complete.", "…step shows Complete.") are unchanged. They are not required: exact-line mode already drops all of them as off-catalog, and A4 names "is complete"-style claims, which are covered.

Reused Stage 2 evidence, matched to the frozen identity:
- `assistant-per-file-3b75306.tsv` has 86 rows. Every row passed; the only non-pass is the pre-existing `test_copilot_model_eval.py` skip. There are no failures or errors.
- `pre-pr-3b75306.log` records HEAD SHA 3b75306 and "SUMMARY: PASS (0 unsafe conditions, 2 warning(s))".
- The backend (4099 passed, 7 known macOS-only failures), frontend (tsc, build, vitest) and affected E2E (10/10) evidence is from e34a5a7. It is still valid because 3b75306 changes only the assistant regex and its test.

Not run by the reviewer: the full E2E suite (not required), physical Mongo (no persistence change), and the full backend and frontend suites (unaffected by the delta). All evidence is local; CI is billing-blocked and nothing here is hosted CI.

## 5. Code and architecture review

- The fix is minimal and readable. The alternation `is|are|was|were|(?:has|have) (adverbs)*been` followed by a mandatory space and optional adverbs keeps every form the old pattern matched, so there is no regression.
- R0's non-required notes still apply, unchanged and optional:
  - The frontend `isAdvisoryReview` does not check `status === "COMPLETE"`. The backend and the assistant do check it.
  - `briefing.ownership_advised` duplicates `guardrails.ownership_review_advised`.
- No scope creep.

## 6. Security review

There are no findings. The flag is a boolean with no PII. It is projected only by the existing authorised GET. The assistant stays GET-only. The exact-line catalog grows by one conditional line and nothing is removed. No guardrail, authority check, maker-checker or permission recheck is relaxed.

## 7. Required fixes

None.

Non-blocking notes: the D-141 number collision with the local `fix/clear-upload-rejections` branch (section 3), and R0's optional notes (section 5).

## 8. Readiness

- D-141 is ready for the PR from a gate perspective. Shane must accept D-141 and its new catalog line before merge.
- Live ACRA and real GoldTier readiness are not affected and not claimed.

## 9. Git status

Branch `fix/advisory-review-status`, HEAD 3b75306, nothing staged. The only change is this untracked report. The reviewer made no implementation, test or configuration edit, no commit, push or merge, and did not start another phase.

Verdict: PASS
