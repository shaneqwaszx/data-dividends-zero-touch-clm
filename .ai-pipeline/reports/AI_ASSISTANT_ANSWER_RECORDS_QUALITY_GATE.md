# AI Assistant answer records - independent quality gate (R0)

## Reviewed content
- Candidate: `970875f061124d95856ee2086a4331252da0313d`, tree `6e0440caa8b3f2c362b42364c05ed6eee28a9c0f`, detached worktree `/Users/tasha/Documents/GitHub/dd-clm-qg-answer-records` (clean at review).
- Base: `origin/main` `a6e86fc`; feature merge-base `5de7f24`. Diff `a6e86fc...970875f`: 20 files, +2626/-57 (assistant code, tests, frontend panel/review/RequestPage, README, .env.example, 6-line ARCHITECTURE edit).
- Decision: D-084 / ADR-012 Amendment 1, PROPOSED (not accepted by Shane). Nothing in the diff claims acceptance.

**Superseded notice:** while this gate was running, the user asked for two more UX changes to PR 2 (compact request rows that open the request page, the "Write the fix" form moved onto the request page, up to 2 earlier exchanges folded under "Earlier in this chat (N)"). That changes the reviewed frontend scope. This verdict covers only the frozen tree above. The changed candidate needs a fresh gate (R1) of the changed delta plus the evidence it invalidates.

## Commands run (this session)
- `pytest -o addopts="" -q -p no:cacheprovider` in `apps/assistant`: **1449 passed** (45 s).
- `ruff check --no-cache .`: all checks passed. `ruff format --check`: 67 files already formatted. `mypy ai_assistant`: no issues in 27 source files.
- Vitest (from the main checkout, same HEAD `970875f`, clean): `AiAssistantPanel.test.tsx` + `KnowledgeReview.test.tsx` **38/38 passed**; full suite **1084/1085**, the 1 failure is the known macOS `ViteHistoryFallback` test, which the diff does not touch.
- `npm run typecheck`: passed (it rewrote the ignored `apps/frontend/dist/` build info in the main checkout; no tracked file changed).
- `git diff --check a6e86fc...970875f`: clean. ARCHITECTURE.md: CRLF count 998 -> 1003 and LF 1096 -> 1101, so the 5 added lines keep main's CRLF.
- Guardrails copy: `tests/test_guardrails_dropped.py` `_main_validate`/`_MainGuard` checked against `git show 5de7f24:apps/assistant/ai_assistant/guardrails.py`. Same selection code word for word (only names and docstrings differ). `_allowed` is unchanged by the diff.
- Adversarial probes (scratchpad only, not in the repo), **5/5 passed**: (1) `add_answer_record` raising -> `/chat` and `/chat/stream` still answer with `answer_id: null`, and a note-only Not helpful is accepted; (2) `owned_answers` raising -> answer intact; (3) Director view with the recheck failing inside the write -> 403 and **no view logged**; (4) a malformed `answer_id` -> 422, nothing stored; (5) a linked record on an open request survives a purge with an old `created_at`.
- Not run (not allowed in this session): E2E. The implementer's E2E claim (2/2 on `1fc06cb`) was not re-checked here.

## Verified
- G6 / exact-line: `Validation.dropped` is `compare=False, repr=False` and only appended to. Kept lines, `left_out` and text are unchanged. `chosen_lines`/`shown_answer` for a model answer are `validation.text` (allowed lines only). Case lines come from fixed templates and backend action labels. Records are never read into prompts or knowledge (test `test_records_never_reach_the_prompt` and code read).
- Redaction: dropped lines are redacted (case Redactor) and capped at 8 KiB of whole lines. A case-data `shown_answer` is redacted. The question is stored unredacted, as D-084 D1 states explicitly. Notes are redacted as on main.
- Access: own record = owner only (others 404, HR 403). Director = POLICY_APPROVE + request scope (RM/HR 403, out-of-scope Director 404). Earlier answers are limited to the head record's `earlier_answer_ids` with the same user and case. Every refusal of an answer is the same `{"code":"NOT_FOUND","message":"No such answer."}`. Views are logged inside `BEGIN IMMEDIATE` after the recheck (`recheck` for a Director, `same_user` for an RM). CLM access stays GET only (`load_case`).
- Feedback: an `answer_id` that is sent is checked (owner, case, unrated, `created_at >= now-7d`) inside the write transaction before insert. A note-only request runs the same path as main #108 (the only SQL change is the `answer_id` subquery in `feedback()`). Rate-once is race-safe (same write lock).
- Retention: unlinked records are purged after 7 days, linked ones 30 days after `closed_at` with status resolved/closed. Open or drafted requests are never purged. Purge runs on start-up and at most hourly in the insert transaction. Views cascade (`PRAGMA foreign_keys = ON` on every connection).
- Schema: the v5 shape change between `7b0fff6` and `07d1e82` is **only** `shown_answer` (diffed both commits); `_repair_5` adds it with JSON default `'""'`. v1-v4 and the branch-only v4/v5 shapes are tested and idempotent.
- Stream: the record is written in `done()` from the guard's validation only. A failure returns the response unchanged.
- Frontend: no fetch without `gap.answer_id` (tested). Escape on the request page goes back, then a second Escape closes. Focus goes to the heading (preventScroll) and returns to the opener. `suggestedCause` rules are applied in order, and there is no hint when the model was unavailable.

## Findings
- **F1 MINOR** `apps/frontend/src/pages/RequestPage.tsx` (`knowledge.thresholds.guidance`, `allowed_lines.map(line => line.text)`). Records written by `7b0fff6` code (branch-only stores, which `_repair_5` keeps on purpose) have `knowledge` without `thresholds`/`kind` and `allowed_lines` as plain strings. Opening a request linked to such a record throws a TypeError in render. The app has no ErrorBoundary, so the whole page unmounts. This hits exactly the local store the repair targets, for up to 30 days after its request closes. Fix: render these defensively (optional `thresholds`, accept string lines), or have `_repair_5` normalise or delete pre-`shown_answer` rows, and add a test with an old-shape record.
- **F2 MINOR** Missing regression test for the core 1fc06cb guarantee: a failure to store the record must leave the answer intact with `answer_id: null` (`/chat` and `/chat/stream`). Probe (1) shows the behaviour is correct, but no committed test covers it. Fix: add that test to `tests/test_answer_records.py`.
- **F3 MINOR (docs)** `docs/decisions/DECISION_LOG.md` D-084 ("nothing is built") and ADR-012 Amendment 1 ("nothing in this amendment is built"; "the question exactly as typed") will be untrue after merge. The code stores the question after the 600-char cut, which the README states correctly. Fix: the PR top must say it is built ahead of acceptance; preferably reword these sentences while keeping status PROPOSED.
- **F4 NOTE** Earlier answers named by an open request are unlinked, so they are purged after 7 days and the Director's "Show earlier answer" then returns "No such answer." This follows D2 as written; raise it with Shane (relevant to the requested "Earlier in this chat (N)" change).
- **F5 NOTE** Small-talk replies show Not helpful with the hint "We couldn't save the details of this answer...", but nothing failed. The wording is slightly misleading; behaviour equals main.
- **F6 NOTE** The record write in the stream path runs synchronous SQLite inside the async generator (it can block the event loop up to the 10 s busy timeout under write contention). This is acceptable for the POC.

## Changed-assertion review (vs a6e86fc)
- `AiAssistantPanel.test.tsx`: the stream `done` fixture gains `answer_id`, and the Not-helpful payload assertion now expects `answer_id`. Justified, and the note-only payload is asserted in the new test "still offers Not helpful when the answer has no record". No weakening.
- `tests/test_knowledge_review.py`: three migration tests now drop the v5 tables before stamping 1/3/4 (so the seeded shape really is old) and expect "5". Justified, with no loss of migration coverage.
- No other existing test changed. The 1fc06cb restorations match main: `git diff a6e86fc...970875f` touches only these test files plus new ones.

## Evidence validity
All counts above are local runs on tree `6e0440ca`. CI is billing-blocked and nothing here is hosted CI. E2E was not verified in this gate. The pending UX change invalidates the frontend evidence for the next candidate.

VERDICT: PASS WITH MINOR FIXES
