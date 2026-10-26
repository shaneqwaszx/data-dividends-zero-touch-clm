# AI Assistant answer records: independent quality gate, round R2

## What was reviewed
- Candidate: `7f854e6` (tree `55a30789c8a3e6f5776726f243e16f361791004c`), checked out detached at `/Users/tasha/Documents/GitHub/dd-clm-qg-answer-records` (clean apart from the untracked R0/R1 reports).
- Baseline: `1d03986`. Full diff `1d03986...7f854e6`. Delta since R1: `ab6c29d..7f854e6`, one commit, 10 files: `apps/assistant` (store, knowledge_api, README, 3 test files), `KnowledgeReview.tsx` and its test, ADR-012 and DECISION_LOG.
- The main checkout `/Users/tasha/Documents/GitHub/data-dividends-zero-touch-clm` is at `7f854e6` with an empty `git status --short`. Frontend checks ran there.
- The reviewer wrote nothing to the repository except this report. Probes are in the scratchpad `probe-r2/`.

## R1 findings: status
- **R1-F1 (earlier answer kept for one request only): RESOLVED.**
  - The link table `answer_record_keeps (record_id, request_id)` has PK (record_id, request_id) and `ON DELETE CASCADE` on the record. Foreign keys are ON in both `_connect` and `_write`.
  - `_keep_earlier` uses `INSERT OR IGNORE ... SELECT ... WHERE user_id/case_id match`, so the same-user and same-case rule is kept.
  - Purge rules:
    - Unlinked: the record has no link and no keep row and is older than N days.
    - Linked: `(linked IS NULL OR linked IN done) AND NOT EXISTS (keep row whose request is not done)`.
  - `_repair_5` creates the table and copies `kept_for_request_id` links. The old column and its index are left in place, unread.
  - Tests:
    - New regression test `test_an_earlier_answer_shown_by_two_requests_stays_until_both_are_done`.
    - The migration test uses the `with-kept-for-column` shape.
  - Probes p4 to p6 pass:
    - p4: linked to an open request and kept for a done one, the record stays; it goes once both are done.
    - p5: a kept, unlinked, aged record survives the unrated rule and the Director can open it.
    - p6: reopening the store is idempotent.
- **R1-F2 (placeholder via reviewer edit): RESOLVED within the stated scope.**
  - An edit of a version with `started_from_answer` that adds a new `[UPPERCASE]` token in its title, body or follow-ups gets 422 `PLACEHOLDER_NOT_REWRITTEN` (`knowledge_api.py:678-692`).
  - Probe p1 covers the title and follow-ups (the shipped test covers the body). Probe p2: an edited version keeps the flag, and the guard applies again.
  - The guard reads the version outside the write lock. This is safe: `revise_pending` checks `expected_hash` inside `_write`, and `started_from_answer` cannot change within a version.
  - Main's tests are unchanged. `test_an_edit_of_any_other_entry_may_still_add_one_as_on_main` documents the boundary.
  - The owner asked that "the API can't publish one" for fixes started from the AI's answer. This scope matches that request. Residual risk is in R2-F2 (NOTE).
- **R1-F3 (docs): RESOLVED.**
  - ADR-012 Amendment 1 now lists:
    - schema v5 with `answer_records`, `answer_record_views` and `answer_record_keeps`;
    - `fix-start` (logged view, no model call, nothing saved);
    - `started_from_answer` (not part of the content hash);
    - the 422 rule, including the edit rule;
    - that the queue question is not a logged view.
  - The migration paragraph covers v1 to v5, branch-only v5 shapes, and rollback: pre-v5 code stamps 4 and v5 code reopens the store unchanged. The rollback probe confirms this.
  - D-084 has an "As built ahead of acceptance" paragraph. Both stay PROPOSED and not accepted. The edit rule appears only in the ADR, not in D-084 (see R2-F3).
- **R1-F4 (UI lost work / hidden follow-ups): RESOLVED.**
  - `refill()` replaces the title or body only while it still equals what the form last filled in (`autoTitle`/`autoBody`).
  - `placeholdersIn` checks follow-ups only for `resolution`.
  - There is a test for each.
- **R1-F5 (fix-start ordering): RESOLVED.**
  - `fix_start` now runs scope, then `require(APPROVE)`, then reach, then the record check, then `load_case`, and only then `request_record`, which does the logged view inside `_write` with the recheck.
  - Tests: `test_no_view_is_logged_when_the_case_cannot_be_loaded`. Probe p3: HR gets 403, an unknown request gets 404 `NOT_FOUND`, and no view is logged.
- **R1-F6 (prefill race test): RESOLVED.** The new vitest "does not overwrite what the Director typed before the start arrived" holds the fix-start response and checks that the typed title survives.

## Commands (this session, local only)
- Assistant `pytest -o addopts="" -q -p no:cacheprovider` (candidate worktree): **1489 passed** in 50.8 s.
- Lint and types:
  - `ruff check --no-cache .`: all checks passed.
  - `ruff format --check --no-cache .`: 68 files already formatted.
  - `mypy ai_assistant`: no issues in 27 source files.
- Frontend (main checkout at 7f854e6, clean):
  - `npx vitest run src/pages/AiAssistantPanel.test.tsx src/pages/KnowledgeReview.test.tsx`: **54/54 passed** in 2 files.
  - `npm run typecheck`: passed with no output.
  - `git status --short` was still empty afterwards.
- `git diff --check 1d03986...7f854e6`: clean.
- Probes (`probe-r2/test_probe_r2.py`, run against the candidate's test fixtures): **6 run, 6 pass, 0 defects**.
- Rollback probe:
  - Seed a v5 store with one keep row.
  - Main `1d03986` store code, extracted by `git archive` into the scratchpad, opens it: stamps 4, keep rows untouched, feedback readable.
  - Reopened with v5 code: stamps 5, keep row intact.
- Not run: E2E and Playwright (forbidden in this session).

## Re-checked broadly (no regression found)
- **Safety controls.** The delta does not touch `guardrails.py`, `briefing.py`, `chat`, or the CLM client.
  - The cumulative guardrails change against main is still only the read-only `dropped` change accepted in R0.
  - No model call was added. CLM access is still GET via `load_case` with the Director's session.
  - Maker-checker and single-reviewer rules are unchanged. `started_from_answer` is provenance only.
  - Permission rechecks stay inside `_write` (`view_answer` with `recheck`, `revise_pending` with `recheck` and `expected_hash`).
  - Redaction on save is unchanged.
- **Refusals.** HR gets 403 before any record check. An out-of-scope or unknown request gets the same `REQUEST_NOT_FOUND`. A missing or foreign record gets the same `No such answer.`
- **Migrations.** Tests cover v1, v2, v3, v4, branch-only v4 shapes, branch-only v5 without `shown_answer`, branch-only v5 with `kept_for_request_id`, and the `started_from_answer` column for every version. Each is idempotent.

## New findings
**R2-F1 NOTE (readiness, not a defect of the reviewed content): `origin/main` has moved, and the merge conflicts.**
- `origin/main` is now `769c149` (#115, "Phase A1 metrics and offline evaluation harness"). The 7f854e6 affected-E2E JSON already records `origin_main: 769c149`.
- #115 changes 5 files this branch also changes: `apps/assistant/ai_assistant/main.py`, `config.py`, `.env.example`, `README.md` and `docs/ARCHITECTURE.md`.
- `git merge-tree 7f854e6 origin/main` reports a **content conflict in `apps/assistant/ai_assistant/main.py`**. That file holds the /chat and stream paths that write answer records.
- This verdict covers only the frozen content against `1d03986`. It does not cover the merged result.
- Required before the PR:
  - merge `769c149` (or newer) into the branch;
  - resolve the `main.py` conflict without losing either the record writes or #115's telemetry;
  - rerun the assistant suite, ruff, mypy and the affected E2E (`assistant-answer-records.e2e.ts:12`, `assistant-streaming.e2e.ts:10`);
  - have the integration delta independently re-gated (a fresh round on the merge commit).

**R2-F2 NOTE (residual scope of the placeholder rule).** These are accepted gaps, not defects:
- Entries not started from the answer may still gain placeholders through an edit (main's behaviour, kept on purpose).
- A started version that already holds a redaction-made placeholder can still be approved; the reviewer judges it.
- A placeholder carries no client data, and the reviewer sees the final text before publishing, so the risk is wording quality only.
- The review card's edit form has no client-side guard. The server's 422 message is shown through `AiAssistantError`.
- List this residual scope in the PR for Shane.

**R2-F3 NOTE (docs precision).**
- D-084's "As built" paragraph says "a fix that keeps a redaction placeholder is refused". It does not mention that edits of started versions may not add one, nor that redaction-made placeholders are kept. ADR Amendment 1 states both.
- Optional: add one clause to D-084 so the text Shane accepts matches the ADR.

## Changed-assertion review (vs `1d03986`)
- `apps/assistant/tests/test_knowledge_review.py`:
  - `DROP_V5_TABLES` now also drops `answer_record_keeps`;
  - the v1, v3 and branch-only v4 migration tests drop the v5 tables and expect "5";
  - the branch-only v4 test re-stamps '4'.
  - These are the expected changes. Migration coverage is not reduced.
- `apps/frontend/src/pages/KnowledgeReview.test.tsx`:
  - four fix and close tests open the request page first;
  - the Tab-wrap last-control assertion is now `[data-open-request="7"]`;
  - the import line gains `age` and `suggestedCause`.
  - These are expected.
- `apps/frontend/src/pages/AiAssistantPanel.test.tsx`: the `done` fixture gains `answer_id`, and the Not-helpful payload expects `answer_id`. Expected.
- No other test that exists on main changed, and no test was deleted. The changes since R1 to branch-owned tests (`kept_for_request_id` assertions replaced by `kept_for()`) are equivalent and follow the schema change.

## Evidence validity (E2E, not rerun here)
- The full run on `ab6c29d` (tree `a97e44f6`, clean, origin_main `1d03986`, `--keep-going`) is complete: 116/116 selected, 107 PASS, 9 ASSERTION_FAILURE. The 9 failures are exactly the listed known ones, and both assistant selectors passed.
  - The JSON shows these are the failing selectors. It does not show that they fail on main; that rests on the implementer's earlier main runs.
- The affected run on `7f854e6` (tree `55a30789`, matching the candidate, clean, selectors-file, no keep-going) passed 2/2.
- Reusing them is **valid for this delta**:
  - The delta touches only `apps/assistant`, `KnowledgeReview.tsx` and its test, and docs.
  - The only browser flows that reach the Director request page and the RM panel are covered by the two rerun selectors.
  - No backend, orchestration or other frontend file changed since `ab6c29d`.
- After R2-F1's integration, these runs are stale for the merged tree and must be rerun as stated there.

## Verdict
The frozen candidate `7f854e6` against baseline `1d03986` resolves R1-F1 to F6. No defects found; the three notes need no code fix in this content. Merge readiness depends separately on R2-F1 (integrate `769c149`, resolve the `main.py` conflict, rerun checks, re-gate).

VERDICT: PASS
