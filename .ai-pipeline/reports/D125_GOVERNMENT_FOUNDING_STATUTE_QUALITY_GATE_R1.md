# D-125 Government founding statute: independent quality-gate recheck (R1)

- Reviewer: the same independent Claude subagent as R0 (did not author or remediate any content).
- Reviewed SHA: **0d4e912** (`0d4e912b5b79ff617b01961429c5ed1f8c4ed0a3`, tree `5b41f1672a6f88d213960464cd40ee0e83da995e`), local only, not pushed.
- Recheck scope: `git diff 9ae3afe 0d4e912` (18 paths, including the committed R0 report; diff sha256
  `2a5db7ef081ee05eed7c789a614b805675534ebaafd22a3e59f408bf6991c134`). Unchanged R0 evidence for
  the rest of `4c1db49..9ae3afe` is reused.
- Working tree clean at start; only this report added.

## 1. Executive Result

**PASS**

M1 is fixed without relaxing any check: `confirm_government_status` is unchanged, and the new
read-only `government_reconfirmation_needs_resume` only drives a browser Continue control that
calls the existing, server-authorised `/resume`. The resume's existing recovery reopens the hold;
the RM then confirms with the statute. L1 (Tasha's rule) is fixed: bracketed text is accepted
only when the document has the same bracketed group, through the same mismatch path that saves
nothing. No new finding needs a fix.

## 2. Acceptance Checklist (delta)

| # | Item | Result | Evidence |
|---|---|---|---|
| M1 | An old confirmation past the hold can be re-confirmed | PASS | `zero_touch_orchestration.py:1030-1056`, `api_models.py:1590-1645`, `main.py:1391`, `GovernmentStatusPanel.tsx:75-81`, `CaseDetail.tsx:1632`; `test_an_old_confirmation_past_the_hold_is_reconfirmed_after_continue` (409 NOT_ALLOWED before Continue, `/resume` with concurrency headers reopens `GOVERNMENT_STATUS_REQUIRED`, confirm 200, target calls `["GET"]`); ran myself |
| M1b | Continue not offered while the hold is open, or once frozen/completed | PASS | guard set mirrors the `government_revoked` branch (OWNERSHIP completed, not COMPLETED/TECHNICAL_FAILURE, no snapshot/result/retained execution, no open hold, gate False); `test_resume_is_not_offered_while_the_government_hold_is_open`; projection sets it only when not confirmed and evidence present |
| M1c | No check relaxed | PASS | `confirm_government_status` untouched in the delta; `/resume` keeps its reauthorization and concurrency headers; Continue is shown under the same `ownership_edit_authorized` gate as the form |
| L1 | Bracketed text only when on the document | PASS | `government_status.py:39-74` (`groups <= document_groups`); normaliser tests and API mismatch test with "(any note)"; my probes below |
| D | Docs consistent with behaviour | PASS | D-125 G2/G5, BPD text, regenerated rectification guide, UAT step 4, persistence profile; boundary `--check` current |

## 3. Contract and Integration Findings

None. No connector, mapping or target payload change. No architecture invariant touched: the
new method is a read-only projection helper; mutation authority stays with the existing
`/resume` and confirmation routes inside their locks.

## 4. Tester and Adversarial Findings

Checks I ran on 0d4e912 (local macOS, not hosted CI):

| Check | Result |
|---|---|
| `pytest` entity types, statute normalisation, statute persistence, entity-types persistence, blocker decision policy, slice_c catalogue, zero_touch_orchestration | 344 passed, 0 failed |
| Physical Mongo :27185 `test_zero_touch_entity_types_real_mongo.py`, `test_phase12_real_mongo.py` | 25 passed |
| vitest `GovernmentStatusPanel.test.tsx` + `CaseDetailGovernmentStatute.test.tsx` | 16/16 |
| `tsc -b --noEmit` | exit 0 |
| ruff / mypy (139 files) | pass / no issues |
| `check_project_state.py`, assistant `build_synthetic_boundary.py --check`, `git diff --check 9ae3afe 0d4e912` | PASS / current / clean |
| E2E selector `e2e/database-classification.e2e.ts:234` (results `scratchpad/qg/e2e_qg_r1_results.json`) | 1/1 PASS |

Bracket probes against `"Demo Parks Act (Amendment (No. 2))"`: `(No 2)`, `(amendment)`, the full
nested group, `((No 2))` and a repeated `(No 2) (No 2)` match (document text only); an unclosed
`(note`, `note)` and `[note]` are mismatches. R0 probes for the legacy path now pass via the new
test. Changed test assertions in the delta: the only moved case is the implementer's own
`"(Cap. 999)"` (accepted -> rejected), matching the agreed L1 rule; no teammate assertion changed.

## 5. Code and Architecture Review

- `_split_statute` keeps the earlier normal form for the unbracketed text, so the R0 normaliser
  results are unchanged; groups are normalised the same way and empty groups dropped.
- `government_reconfirmation_needs_resume` runs on every case projection; it returns early for
  missing records and `_government_gate` returns None for non-Government cases. Cost is a few
  repository reads, the same as neighbouring projection helpers.

## 6. Security Review

L1 is closed: arbitrary bracketed notes (including PII-style notes) are refused before anything
is saved. Advisory only (no fix required): invisible characters that `\W` turns into spaces, for
example a zero-width space inside or outside brackets (`"Demo Parks Act (​)"`), still match
and are stored verbatim. They carry no readable text; this is part of R0's L2 (no Unicode
normalisation).

## 7. Required Fixes

None.

Advisory (unchanged from R0 or new, for the PR body; not blocking): R0 L2-L5; zero-width
characters as above; the Continue banner text names the pre-D-125 reason, which is the only
known way to reach `resume_required` today; if another revocation path appears later, make
the text generic.

## 8. Readiness

Ready to proceed to the remaining Stage 2/4 steps (pre-PR check on a clean committed tree,
merge-readiness report, ask Tasha before push). Mock/Local only; no live ACRA or real GoldTier
claim. Shane must still accept D-125 (candidate) and any manual-CI exception.

## 9. Git Status

- Branch `feat/d125-government-founding-statute`, HEAD 0d4e912, not pushed.
- No staged or tracked changes; untracked: only this report. The R0 report (committed) was not modified.
- Scratch probes and E2E artefacts are in the session scratchpad `qg/` folder.
- No implementation fix, commit, push, merge, rebase, reset, stash or branch change by the
  reviewer. `.env` was not read.
