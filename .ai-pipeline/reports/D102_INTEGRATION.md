# D-102 latest-main integration and evidence (2026-10-30)

Implementer report (not an independent review). Branch `feat/claude-hr-spending-d102-int`,
worktree `C:\Users\shane\Desktop\claude-worktrees\claude-hr-spending-d102-int-20261030`, cut
from `origin/main` `2911b54fb78b2503e80511c0cc3fc54eae37e37f` (PR #133, fetched and verified
2026-10-30). The original branch `feat/claude-hr-spending-d102` and its commit `93d154d` are
kept unchanged. Nothing is pushed; no paid, provider or network call was made.

## 1. What was integrated

| Commit | Content |
| --- | --- |
| `403d5c2` (tree `20644942a7e6`) | Cherry-pick of the reviewed D-102 commit `93d154d` (tree `c8113e99`, content fingerprint `e4f58e36e17c…`, re-QG PASS) |
| docs-only commit (this report's commit) | D-102 owner acceptance, the two QG reports, this report, a PROJECT_STATE delta |

**Conflict resolution.** None was needed. Git applied the cherry-pick cleanly: PR #133 changed
one line near line 224 of `docs/PROJECT_STATE.md`, and D-102 appends its own dated section at
the end. Both histories are kept.

**Identity of the reviewed content.** For every file in the D-102 commit, the blob in `403d5c2`
was compared with the blob in `93d154d`: 13 of 14 are byte-identical (all application code,
tests, `DECISION_LOG.md` and `AI_MODEL_CONFIGURATION.md`). `docs/PROJECT_STATE.md` differs only
because its base now includes PR #133; the lines D-102 adds are exactly the reviewed ones
(the +/- lines of `d90ab6a..93d154d` equal those of `2911b54..403d5c2` for that file).
`git diff 93d154d 403d5c2 -- apps/assistant` is empty. PR #133 touches none of D-102's files
apart from `docs/PROJECT_STATE.md`.

## 2. Evidence sources (verbatim copies)

| File | Source | sha256 |
| --- | --- | --- |
| `D102_QUALITY_GATE.md` | independent QG of `f1d32387…` (CONDITIONAL PASS) | `e73653827e2cd3d3ed5161daea4adf2929c83363d3bb55e294beed8e2de33ef3` |
| `D102_REQG.md` | independent re-QG of `e4f58e36…` (PASS) | `3ad0570517d521cabbfb35b7f1030ef6bb12001e7690bd4f2ab33dcd0f6d7c3e` |

Both were written by separate review agents outside the candidate worktree, copied unchanged
(hashes match the originals), and contain no key, token or workspace identifier.

## 3. Validation on the integrated tree (`403d5c2` code)

| Check | Result |
| --- | --- |
| Focused assistant suites (`test_claude_hr_spending`, `test_claude_runtime`, `test_claude_console`, `test_d098_recovery`, `test_model_management`, `test_remote_test`, `test_budget_cli`, `test_spending_controls`) | all pass except `test_remote_test.py::test_the_boundary_file_is_current` (see section 4) |
| Full assistant suite | 2,860 tests: 2,845 passed, 15 failed. 14 are `OSError: [Errno 24] Too many open files`, the same 14 test ids as on the reviewed candidate and on unmodified main, and they pass when run alone. 1 is the main-inherited boundary failure (section 4). **Not a clean full-suite PASS.** |
| Frontend | vitest 67 files, 1,218 passed (the reviewed 1,210 plus PR #133's tests); typecheck pass; build pass (output outside the repo) |
| Browser check, MOCK requests only (Playwright, Vite on 127.0.0.1, every `/api` request served from a fixture dumped from the offline test journey) | Desktop 1280x900 and mobile 375x812: the Claude panel renders with labelled inputs, no horizontal overflow, Save disabled until the call-raise confirmation is ticked, and the save sends `{expected_revision, daily_cap_micro_usd, max_calls: 15, confirm_max_calls: 15}` to the Claude route only; no OpenRouter wording in the Claude panel. Unmocked requests: only the page banner's `/api/system/execution-profile` (answered 404) and Google Fonts (blocked). Cosmetic, pre-existing: the floating assistant button overlaps the right edge of the per-configuration figures at 375 px |
| Synthetic boundary `--check` | **fails on the integrated tree and on main `2911b54` alone** (section 4) |
| Qualification basis | unchanged by the integration (no basis file differs from the reviewed commit) |

## 4. Blocker inherited from main (not D-102)

Main `2911b54` (PR #133) fails `test_the_boundary_file_is_current` on its own: PR #133 added
the backend string `onboarded` (`apps/backend/app/domain/case_management.py`), and the
synthetic boundary's code vocabulary is built from backend string constants. Regenerating the
boundary adds that one word (`code_vocabulary`, nothing removed), and because
`synthetic_boundary.json` is a qualification-basis file it would move the basis again. This
branch does not change it: boundary vocabulary changes have needed owner acknowledgement, and
this run was not authorised to change the basis or PR #133's area. It needs an owner decision:
fix it on main separately, or authorise it here.

## 5. Accepted limitations carried forward

L4, N1 and I1 as recorded in D-102; the 14 Windows `Errno 24` failures as an environmental
limitation; no hosted CI (billing-blocked); no live Anthropic call.
