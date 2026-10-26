# AI Assistant answer records: quality gate R3 (merge of #115)

- Reviewer: independent quality-gate subagent (did not write this code).
- Reviewed commit: `dcd3b0c` (tree `1c34bd41144d82e1d5ec1765f1f7109f9f59d957`), detached at `/Users/tasha/Documents/GitHub/dd-clm-qg-answer-records`. The worktree was clean apart from the untracked gate reports.
- Parents: `7f854e6` (R2 PASS against `1d03986`) and `769c149` (origin/main, #115 "Phase A1 metrics and offline evaluation harness").
- Scope: the merge resolution that R2-F1 asked for. That is the `apps/assistant/ai_assistant/main.py` conflict, the four auto-merged shared files, and whether #115's content was kept.
- Evidence is local only. CI is billing-blocked, and nothing here is hosted CI.

## 1. main.py against both parents
- **`git diff 769c149 dcd3b0c -- main.py` (main to merge).** This diff holds only the branch's answer-record changes:
  - the module docstring line;
  - the `answer_records` imports, with `FallbackReason` aliased to `RecordReason` so it does not shadow telemetry's `FallbackReason`;
  - the `Redactor`/`case_parties` import;
  - `ChatRequest.earlier_answer_ids`, and `ChatResponse.answer_id` and `small_talk`;
  - `Prepared.question` and `started`;
  - the `AnswerRecorder` (now `answers`) with its start-up purge;
  - `record()`, `prepare()` stamping `started`/`question`, `answer_days=` on the router, and `case_id: UUID` on both routes;
  - `small_talk=True` on both small-talk replies.
  - Two things are new to the resolution: `_Outcome.validation`, set in `selected()`, and `_Outcome.record_reason()`.
  - Every line of #115 is still present. Only three of its lines were rewritten, and each one only wraps the response: `done()` now returns `finish(outcome.answered(response), outcome)`, `/chat` wraps `answer_with_model` in `record(...)`, and `stream_answer` gains a `finish` argument.
- **`git diff 7f854e6 dcd3b0c -- main.py` (branch to merge).** I compared it line by line, after sorting, with `git diff 1d03986 769c149 -- main.py`.
  - The lines that differ are the expected ones. The branch's tuple-returning `answer_with_model` and its `reason`/`checked` locals are replaced by `_Outcome`. `record()` takes `outcome` in place of `(validation, reason)`. `recorder` is renamed to `answers`, because #115 already uses `recorder` for metrics.
  - No telemetry line of #115 is missing. No answer-record behaviour of the branch is missing (see section 2).
- **Shared auto-merged files.** For `config.py`, `.env.example`, `README.md` and `docs/ARCHITECTURE.md`, the branch-side diff (`1d03986..7f854e6` against `769c149..dcd3b0c`) and the main-side diff (`1d03986..769c149` against `7f854e6..dcd3b0c`) are identical.
- **Other files.**
  - Every file that only #115 touched is byte-identical to `769c149`. That covers telemetry.py, assistant_eval/*, scripts/evaluate_answers.py, the eval fixtures, test_telemetry.py, test_eval_harness.py and the six `.ai-pipeline` docs.
  - Every file that only the branch touched is byte-identical to `7f854e6`.
  - The merge changed no file that neither side touched.
- **Line endings.** `docs/ARCHITECTURE.md` has mixed line endings on both sides. It has 98 LF-only lines at `1d03986`, `769c149`, `7f854e6` and `dcd3b0c` alike, and its CRLF lines are kept.
- **Frontend.** #115 changed no frontend file. Its 27 paths are all `.ai-pipeline/`, `apps/assistant/` and `docs/ARCHITECTURE.md`.

## 2. Answer-record equivalence across paths (probe)
- **Method.** I extracted `7f854e6` and `dcd3b0c` with `git archive` into `scratchpad/probe-r3/{base,merge}`. I ran the same probe (`probe-r3/test_probe_r3.py`) in each tree, with a knowledge store on and a scripted model, and compared the recorded `fallback_reason`, `left_out`, `answered_by`, `notices`, `dropped_lines`, `chosen_lines` and `model`.
- **Result.** All 15 scenarios match: 0 differences.

| Scenario | Record reason | left_out | dropped | chosen | Metrics reason |
|---|---|---|---|---|---|
| chat model answer | None | 0 | 0 | 1 | none |
| chat model answer with a left-out line | None | 1 | 1 | 1 | none |
| chat cut short | cut_short | 0 | 0 | 1 | none (cut_short flag) |
| chat nothing allowed | nothing_allowed | 1 | 1 | 0 | policy_no_allowed_line |
| chat model unavailable | model_unavailable | 0 | 0 | 0 | model_unavailable |
| chat model disabled | model_unavailable | 0 | 0 | 0 | model_disabled |
| stream full (with a left-out line) | None | 1 | 1 | 1 | none |
| stream full, cut short | cut_short | 0 | 0 | 1 | none |
| stream partial, cut short | cut_short | 1 | 1 | 1 | stream_partial |
| stream nothing allowed | nothing_allowed | 1 | 1 | 0 | policy_no_allowed_line |
| stream nothing allowed + length cut | nothing_allowed | 1 | 1 | 0 | policy_no_allowed_line |
| stream failure, left-out lines, no text | model_unavailable | 1 | 1 | 0 | model_unavailable |
| stream failure, nothing at all | model_unavailable | 0 | 0 | 0 | model_unavailable |
| stream model unavailable | model_unavailable | 0 | 0 | 0 | model_unavailable |
| stream model disabled | model_unavailable | 0 | 0 | 0 | model_disabled |

- **Why the "failure, no text" case still matches.** The branch recorded `partial` only when `partial.left_out` was non-zero. The merge always calls `selected(partial)`. These are equivalent because `Validation.dropped` and `left_out` grow together (`guardrails.py:520-534`, `562-619`), so an empty `left_out` means an empty `dropped`.

## 3. Telemetry stays content-free and unchanged
- **Metrics never see the record.**
  - `emit()` reads only `outcome` and `prep`. It never reads `response`, `answer_id` or `outcome.validation`. `AnswerMetrics` has no `validation` or `answer_id` field (probe).
  - `record()` only reads `outcome`. `outcome.answered()` runs before `finish`/`record` adds `answer_id`, so `cited_sources` is computed on the same response as on main.
- **Metrics content (probe, all 15 paths).** The metrics JSON never contained the `answer_id`, the allowed line, the dropped text, or the UEN. There was exactly 1 metrics record per request.
- **`record_reason()` cannot raise.** It only compares closed literals. It was probed with all 6 telemetry reasons, plus an unknown one, with `cut_short` both on and off.
- **Record failures.**
  - The record work sits inside `record()`'s `try/except Exception`.
  - On the stream, `finish` runs inside main's `try/finally`, so `emit` still runs exactly once. That includes cancellation (`delivered=False` leads to `cancelled=True`).
  - Probe: with `add_answer_record` raising, both `/chat` and `/chat/stream` still returned the model answer with `answer_id=None`, and wrote 1 metrics record with `answered_by=model`.
  - #115's `test_a_client_that_disconnects_mid_stream_is_recorded_as_cancelled`, `test_answers_are_byte_identical_with_and_without_metrics` and `test_a_failing_sink_never_changes_the_answer` pass, as does the branch's `test_an_answer_whose_record_cannot_be_saved_is_still_given[chat|chat/stream]`.
- **Order on `/chat`.** `record` runs before `emit`. Only the profile lookup in `record()` runs outside its `try`. That code is unchanged since R0, and the same ordering rule applies to main's own `answer_with_model`.

## 4. Safety controls
- `guardrails.py`, `briefing.py`, `clm_client.py`, `knowledge/redaction.py`, `knowledge_api.py` and `answer_records.py` are byte-identical to `7f854e6`. The cumulative guardrails change against main is still only the read-only `dropped` change accepted in R0.
- The exact-line catalog and G6 are unchanged.
- `main.py` still calls the model only through `model.complete`, `model.stream` and `model.warm`. No new model call was added.
- CLM access is still GET through `backend.load_case`.
- Redaction of dropped lines and case-data answers is unchanged.
- The permission rechecks inside writes live in files the merge did not touch.

## 5. #115 content kept
- Every #115-only file is byte-identical to `769c149` (section 1).
- `ARCHITECTURE.md` line endings are kept (section 1).

## 6. Commands and counts (run one at a time)
| Command | Result |
|---|---|
| `.venv/bin/python -m pytest -o addopts=""` (apps/assistant, worktree at dcd3b0c) | **1574 passed** in 69.04s |
| `ruff check .` | All checks passed |
| `ruff format --check .` | 81 files already formatted |
| `mypy ai_assistant` | Success: no issues found in 28 source files |
| `npx vitest run src/pages/AiAssistantPanel.test.tsx src/pages/KnowledgeReview.test.tsx src/aiAssistant.test.ts` (main checkout, HEAD dcd3b0c, clean) | 3 files, **56 passed** (37 + 17 + 2) |
| `npm run typecheck` | exit 0 |
| Probe `test_probe_r3.py` in the merge tree | 4 passed |
| Probe `test_probe_r3.py` in the base tree | 1 passed, 3 skipped (the metrics-only tests) |
| Equivalence diff of the two probes | 15 scenarios, 0 differences |

- No servers, E2E or Playwright were run by this gate.

## Findings
**R3-F1 NOTE (comment accuracy).** `apps/assistant/ai_assistant/main.py:207`
- Problem: the `_Outcome` docstring still says it is "kept only for its content-free metrics". It now also carries `validation`, which holds the dropped model text, for the answer record.
- Why it matters: the field comment at lines 218-219 says the field is never part of the metrics, and the code is correct. A later maintainer adding a metrics field from `_Outcome` could still be misled by the class docstring.
- Optional fix: reword it to "...for its content-free metrics (telemetry.py), and the check the answer record keeps (`validation`, never in metrics)".

**R3-F2 NOTE (interaction, not a defect).** `apps/assistant/assistant_eval/runner.py:221-229`
- What happens: since the merge, the #115 offline harness (`create_app(..., knowledge=..., knowledge_enabled=True)`) also writes answer records, holding synthetic questions, into its temporary per-run knowledge stores.
- Why it is acceptable: those stores are always a `Workspace()` temp folder, removed on close, and the CLI has no option to point at the real store. The harness reads only `answer`, `answered_by` and `sources` from `done`, so the random `answer_id` does not affect its scores or fixtures (`test_eval_harness.py` passes).
- Optional: mention this in the PR so Shane knows the harness exercises the record path too.

**R3-F3 NOTE (docs wording).** `apps/assistant/README.md:353-362`
- Problem: the Observability section uses "A record holds only counts..." for a metrics record. The same README describes "answer records", which do hold the question.
- Why it is minor: the section headings make the meaning clear.
- Optional fix: say "A metrics record" there.

No BLOCKER, MAJOR or MINOR findings.

## Evidence validity (E2E, not rerun here)
- **Affected run, valid for this merge.** `scratchpad/pr2-e2e-affected-dcd3b0c.json` identifies head `dcd3b0c` and tree `1c34bd41`, which match the reviewed commit. It was clean, with origin_main `769c149`, mode selectors-file and no keep-going. It ran 2/2 PASS (`assistant-answer-records.e2e.ts:12`, `assistant-streaming.e2e.ts:10`).
- **Full run, still usable as the regression baseline.** `scratchpad/pr2-full-e2e-ab6c29d.json` is on `ab6c29d` (tree `a97e44f6`, origin_main `1d03986`, `--keep-going`): 116 selected, 107 PASS, 9 ASSERTION_FAILURE.
  - Since then only two things landed: `7f854e6`, already accepted in R2, and #115.
  - #115 is assistant-only: telemetry is off by default, plus an offline harness. It changes no frontend, backend or orchestration file.
  - The merge's only behavioural surface reachable from the browser is the assistant's chat and stream paths, which the two affected selectors cover on the exact tree.
  - Caveats: that run used `--keep-going` (a diagnostic mode). The claim that the 9 failures also fail on main still rests on the implementer's earlier main runs. If the final acceptance requires a fresh full run, it is still owed. This gate does not replace it.

## Verdict
The merge resolution keeps all of #115's telemetry and all of the branch's answer-record behaviour. The record fields are the same as before the merge on all 15 paths probed. The metrics stay content-free, `emit` still runs exactly once per request, and no safety control changed. The three notes need no code change.

VERDICT: PASS
