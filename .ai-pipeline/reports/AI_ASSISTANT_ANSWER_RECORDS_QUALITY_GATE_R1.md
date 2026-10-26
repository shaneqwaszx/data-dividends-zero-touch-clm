# AI Assistant answer records - independent quality gate (R1)

## Reviewed content
- Candidate: `ab6c29dfda8dadb60cc7a181b5d0f09ebb73fe5c`, tree `a97e44f63a4d0228ea4382a98af6adc6b8600942`, detached worktree `/Users/tasha/Documents/GitHub/dd-clm-qg-answer-records` (clean apart from the untracked R0 report).
- Baseline `origin/main` `1d03986`; merge-base `5de7f24`; merges of main `970875f` (a6e86fc) and `4ac4339` (1d03986).
- Feature diff `1d03986...ab6c29d`: 24 files, +3905/-161. The two-dot diff `1d03986 ab6c29d` gives the same 24 files, so every main change (D-085 to D-089, backend, ownership UI, teammates' tests) is kept byte for byte; nothing under `apps/backend`, ownership pages or other teammates' tests differs from main.
- Delta since R0 (`970875f`): `41c7e91`, `200e279`, `4ac4339` (merge), `a280e43`, `ab6c29d`. `guardrails.py` and `test_guardrails_dropped.py` are unchanged since R0 (R0 verified the copy of main's selection code against `5de7f24`). Main did not change `apps/assistant` between `5de7f24` and `1d03986`.
- Decisions: D-083 and D-084 stay PROPOSED. D-084 now says D1/D2 were built ahead of acceptance and the PR does not merge until Shane accepts. D-085 to D-089 unchanged.
- Main checkout `/Users/tasha/Documents/GitHub/data-dividends-zero-touch-clm`: HEAD `ab6c29d`, `git status --short` empty, `apps/frontend/src` identical to the candidate. Used only to run vitest and typecheck; nothing written there.

## R0 findings
- **F1 (old-shape record crashes the request page): RESOLVED.** `RequestPage.tsx` treats `knowledge.thresholds` as optional and accepts plain-string allowed lines (`allowedLine`, line 59). Test "shows a record from the first build of answer records without breaking".
- **F2 (no test for a failed record write): RESOLVED.** `test_an_answer_whose_record_cannot_be_saved_is_still_given` is parametrized over `chat` and `chat/stream` and checks the answer, `answer_id: null` and `small_talk: false`.
- **F3 (docs say "nothing is built" and "exactly as typed"): RESOLVED.** D-084 status, ADR-012 Amendment 1 and D-084's closing text now say built ahead of acceptance and "cut at 600 characters". Still PROPOSED.
- **F4 (earlier answers purged after 7 days): RESOLVED for the single-request case** with `kept_for_request_id`. The two-request case is still open, see R1-F1.
- **F5 (misleading small-talk hint): RESOLVED.** `small_talk: true` on both paths; the panel hides the hint for small talk (tests on both sides).
- **F6 (sync SQLite in the stream generator): unchanged NOTE**, accepted for the POC.

## Commands (this session, local)
- Assistant `pytest -o addopts="" -q -p no:cacheprovider` (candidate worktree): **1484 passed** (43 s). This is the first full assistant run on `ab6c29d`.
- `ruff check --no-cache .`: all checks passed. `ruff format --check --no-cache .`: 68 files already formatted. `mypy ai_assistant`: no issues in 27 source files.
- Vitest (main checkout, same content) `src/pages/AiAssistantPanel.test.tsx src/pages/KnowledgeReview.test.tsx`: **51/51 passed** (17 + 34). The full frontend suite was not rerun; the only files it would add are untouched by the diff, apart from the known macOS `ViteHistoryFallback` failure.
- `npm run typecheck`: passed. Afterwards the main checkout's `git status --short` was still empty.
- `git diff --check 1d03986...ab6c29d`: clean. `docs/ARCHITECTURE.md`: CR lines 1007 -> 1012 and total lines 1105 -> 1110, so the 5 added lines keep main's CRLF.
- Adversarial probes (scratchpad `probe-r1/`, not in the repo): **4 run, 2 show defects.**
  1. An earlier answer named by two requests: **FAIL** (R1-F1).
  2. Reviewer edit endpoint with `[ADDRESS]` in the body: **accepted with 200** (R1-F2).
  3. `fix-start`: HR 403, RM 403, unknown request 404, no view logged: pass.
  4. `feedback()` LEFT JOIN returns one row per request: pass.
- Rollback probe: main's `1d03986` store code opens a v5 store (stamps 4, reads feedback). Reopening it with v5 code stamps 5 again and keeps the record link: pass.
- Not run: E2E and Playwright (forbidden in this session; a full run was in progress in the main checkout). The implementer's E2E claim for `assistant-answer-records.e2e.ts:12` is **not verified** by this gate.

## Verified
- **Safety controls.** Exact-line catalog and G6: no change since R0. Model `chosen_lines` and `shown_answer` are `validation.text` only. No new model call: `fix-start` is pure record text plus the Redactor (`test_no_model_is_called_for_the_fix_start`). Records never enter a prompt or knowledge. CLM access stays `load_case` (GET), using the Director's own session for `fix-start` and draft.
- **Maker-checker.** Unchanged. `started_from_answer` is provenance only: it is not in `content_hash` (checked in `models.py`) and has no effect on review rules.
- **Permission rechecks.** Views (own, request, earlier, fix-start) are logged inside `_write(authorize)` after the recheck. Feedback rating checks owner, case, unrated and age inside the write.
- **Access and enumeration.** HR is 403 before any placeholder or record check. An out-of-scope or unknown request gives the same `REQUEST_NOT_FOUND`. An in-scope request without a record, a foreign or old earlier answer, or a made-up id gives the identical `{"code":"NOT_FOUND","message":"No such answer."}`. A Director can open only `earlier_shown(head)` with the head's user and case.
- **Fix prefill.** Lines are redacted before splitting and again per sentence. Notices and `POLICY_LINES` are skipped. The title comes from the first blocker code. In practice the "shown non-allowed" branch is empty for model answers, because chosen lines are always allowed lines; it is defensive only. Server-side `started = body.started_from_answer and request_row["answer_id"] is not None`. A reviewer edit keeps the flag (`with_changes`).
- **Persistence.** v1, v2, v3, v4, branch-only v5 without `shown_answer`, branch-only v5 without `kept_for_request_id`, and v1 to v5 without `entries.started_from_answer` are all migrated and idempotent (tests plus code read). `_add_entry_origin` runs for every existing store before `_SCHEMA`. Purge SQL: unlinked rows go after N days; a linked or kept row goes only when every request it references is resolved or closed and older than the cutoff; views cascade. The LEFT JOIN cannot duplicate rows, because each feedback insert links at most one record (rate-once in the same write).
- **Frontend.**
  - The request page focuses the heading. Escape goes back first, then closes. Back returns focus to the row. Tab wrap uses the live `dialog` ref.
  - No `/answer` or `/fix-start` fetch without `answer_id` (tested).
  - The prefill does not overwrite a typed fix (`all[id] ? all : ...`, code read; no dedicated test). Clear is respected on reopen (`fixes[id]` is set, so no refetch).
  - Save is disabled while a placeholder is left, with the stated message. Choosing a guidance change starts from the current title and text.
  - Phone layout: `.request-page-columns` stacks under 900 px.
- **Docs.** README and `.env.example` match the config (`AI_ASSISTANT_ANSWER_RECORD_*`, 7/30). ARCHITECTURE keeps CRLF.

## Findings

**R1-F1 MINOR: an earlier answer is kept for only the first request that names it.**
- Where: `apps/assistant/ai_assistant/knowledge/store.py:965-980` (`_keep_earlier` sets the single `kept_for_request_id` only `IS NULL`) and the purge at `:1150-1166`.
- Failure scenario (reproduced by probe 1):
  1. A chat has answers A1, A2, A3. "Not helpful" on A2 creates R1 and keeps A1 for R1.
  2. "Not helpful" on A3 creates R2, which shows A1 and A2. A1 stays tied to R1 only.
  3. R1 is closed and 30 days pass while R2 is still open. The purge deletes A1.
  4. R2's Director then sees "This earlier answer is no longer available."
- This contradicts the owner-approved rule and the docs: ADR-012 Amendment 1 says the earlier answers a Director is shown "are kept with it ... a record tied to two requests stays until both have ended"; the README says the same. No data leaks and the UI degrades gracefully, so this is MINOR, but it is a retention-contract gap.
- Required fix: track every keeping request. Either add a link table `(record_id, request_id)`, or have the purge also spare any record listed in `earlier_shown(...)` of a record linked to a request that is not yet done. Add a regression test for this scenario.

**R1-F2 MINOR: the placeholder guard can be bypassed through the reviewer edit path.**
- Where: `apps/assistant/ai_assistant/knowledge_api.py:651-689` (`/entries/{id}/versions/{v}/edit`) and the review card's edit form in `KnowledgeReview.tsx`.
- The draft endpoint checks placeholders at `knowledge_api.py:776`. The edit endpoint and the review card do not.
- Reproduced by probe 2: a Director saves a clean fix, edits the pending version to "Ask [ADDRESS] for the lease." and gets 200. In single-reviewer mode the same Director can then publish it after "Confirm and publish". So a placeholder can be published through the API and the UI.
- Separately, and within the stated scope (no defect): redaction on save can itself put placeholders into a saved fix when the Director types a client value.
- The placeholders carry no client data and a reviewer sees the final text, so this is a quality gap, not a safety one.
- Required fix: apply `placeholders_left` to the edit endpoint for title, body and follow-ups (and the same UI guard on the review card's edit form). Alternatively, record the edit path as an explicit, owner-accepted exclusion in the PR.

**R1-F3 MINOR (docs/governance): what Shane is asked to accept does not describe everything built.**
- Where: `docs/decisions/DECISION_LOG.md` D-084 and `docs/decisions/ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md` Amendment 1.
- These are the texts whose acceptance gates the merge. They say "every view is logged" (D1) and describe schema v5 as the answer-record tables. They do not mention:
  - `GET .../fix-start`: a new Director read of the record, logged, which loads the case;
  - the new `entries.started_from_answer` column in schema v5;
  - the new 422 `PLACEHOLDER_NOT_REWRITTEN` save rule;
  - that the queue shows each request's unredacted question without a logged view (accepted by Tasha, documented only in README line 169, and contrary to D1's "every view is logged").
- ADR "Migration and retirement implications" still stops at v4. The rollback probe shows main's code can open a v5 store, but this is not written down.
- Required fix: add these to D-084 or Amendment 1 (keep PROPOSED), or list them explicitly at the top of the PR for Shane's decision.

**R1-F4 MINOR (UI): two ways typed work is lost or Save is blocked.**
- Where: `apps/frontend/src/pages/KnowledgeReview.tsx:355-357` and `:43`.
- (a) On a fix started from the answer, changing "Fix as" resets the title and body to the start lines. A Director who already rewrote the placeholders loses that work silently, and the placeholders come back.
- (b) `placeholdersIn` also checks `followUps` when the kind is guidance, where that field is hidden and not sent. A placeholder typed into the follow-ups before switching to Guidance change keeps Save disabled, with a "Rewrite [X]" message for a field the Director cannot see.
- Required fix: (a) reset only when the body is still the untouched start text, or ask first; (b) check `followUps` only for `resolution`. Add tests.

**R1-F5 NOTE.** `fix_start` (`knowledge_api.py:552`) logs the record view before it loads the case. If the Director's case load fails, a view is logged and nothing is returned. This is acceptable, because the record was read server-side.

**R1-F6 NOTE.** There is no test for the prefill race (the Director types before `fix-start` resolves). The code is correct on inspection.

## Changed-assertion review (vs `1d03986`)
- `apps/assistant/tests/test_knowledge_review.py`:
  - three migration tests (v1, v3, branch-only v4) now drop the v5 tables first and expect "5";
  - the branch-only v4 test also re-stamps '4' in the same script, which is needed because seeding uses the current store.
  - Justified; migration coverage is not reduced.
- `apps/frontend/src/pages/KnowledgeReview.test.tsx`:
  - four fix and close tests now reach the form through `openFix(view, 7)` (the request page); their payload, disabled-state and message assertions are unchanged;
  - one Tab-wrap assertion: the last control is now `[data-open-request="7"]` instead of the request's reason input.
  - Both follow the owner-approved move of the fix onto the request page. Not weakened.
- `apps/frontend/src/pages/AiAssistantPanel.test.tsx`: the stream `done` fixture gains `answer_id`, and the Not-helpful payload now expects `answer_id` (as in R0). The note-only payload is covered by a new test. Not weakened.
- No other existing test in main's or teammates' files changed (the two-dot diff equals the feature diff).

## Evidence validity
All results above are local runs on tree `a97e44f6` (frontend on identical content in the main checkout). CI is billing-blocked; nothing here is hosted CI. E2E was not run or verified by this gate. The implementer's E2E claim and the in-progress full E2E run in the main checkout remain the implementer's evidence until they are reported.

## Decision
Acceptance is substantially met. The safety controls (exact-line catalog, maker-checker, rechecks inside the write lock, redaction, GET-only CLM access, no new model call) are intact, and the access and enumeration behaviour is correct. The four MINOR findings are bounded:
- a retention edge case with graceful degradation;
- a quality guard that is bypassable on the edit path and carries no client data;
- governance text to complete for Shane;
- two UI form edge cases.

None is a security, contract or false-success defect. Merge also still requires Shane's acceptance of D-084 (and D-083).

VERDICT: PASS WITH MINOR FIXES
