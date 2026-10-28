# AI Assistant D-094 in-app OpenRouter test mode - Independent Quality Gate

Date: 2026-10-28. Reviewer: independent QG (did not author or remediate the candidate).
Scope: the owner's revised D-094 directive (2026-10-27): GPT-OSS 120B via OpenRouter selectable
on the existing AI Models page and used by the existing RM chat, only inside an approved
synthetic boundary, default off, fail closed.

## Verdict

**FAIL**

One High finding: the synthetic-boundary text check can be bypassed. Text in non-ASCII
scripts (Chinese, Cyrillic and others), full-width digits and letters, ISO dates, UUIDs,
readable dates and identifiers split into groups of two digits or fewer are not checked. In an
offline journey test with a mock OpenRouter, a typed Chinese name, a full-width NRIC and a date
of birth reached the mock OpenRouter on both `/chat` and `/chat/stream`. That breaks owner
safety condition (4), and the D-094 known-limit text and the guides overstate what the check
does. Two Medium findings also block a PASS: the streamed chat path blocks the event loop, and
the main journey test is flaky. Everything else verified (default-off behaviour, gate
ownership, the unchanged refactor, admin integration, docs status, hygiene) is recorded below
and can be reused at recheck.

## Frozen content identity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\assistant-openrouter-local-test-20261027`,
  branch `feat/assistant-openrouter-local-test-20261027`, HEAD = base = origin/main `c36b8af`.
- Candidate is uncommitted: 18 modified tracked files and 6 new files (listed in the brief and
  confirmed by `git status`). Nothing is staged.
- Tracked diff sha256 `70f5dcfe7227281bd18d5ae8b2a0195608deb704f33dc8381394e66d60477271`.
- CONTENT ID at START: `b3f9631796dbf099df5828276ed7843229191e6aa709ec2149e1d619749ba031` (matches the brief).
- CONTENT ID at END: `b3f9631796dbf099df5828276ed7843229191e6aa709ec2149e1d619749ba031` (unchanged; verdict applies to this content)

## Findings

| # | Severity | Location | Finding |
| --- | --- | --- | --- |
| F-1 | **High** | `apps/assistant/ai_assistant/synthetic_boundary.py:39-62,190-197` | **The vocabulary check misses whole classes of text.** (a) `_TOKEN = [a-z0-9]+` runs after `lower()`, so any character outside ASCII letters and digits produces no token and is never checked: CJK, Cyrillic, Greek, Tamil, accented letters (split, not refused) and full-width forms. (b) `normalize` replaces ISO dates/times, UUIDs and readable dates with `<t>` **in user and history messages too**, so a date of birth or a UUID-shaped identifier passes. (c) Digit tokens of two characters or fewer always pass, so `S 12 34 56 7` passes (`s` is in the conversation vocabulary). Reproduced through `check()`: `客户陈伟明的身份证号码是 Ｓ１２３４５６７Ｄ…` → `None` (inside the boundary). Cyrillic name and passport → `None`. `What should I do next? 1985-03-12` → `None`. A UUID → `None`. `S 12 34 56 7 what next?` → `None`. History `客户陈伟明 护照 Ｅ１２３４５６７` → `None`. **End to end:** with the `Journey` harness (HR activates through the page, the RM asks), the question `客户陈伟明 身份证 Ｓ１２３４５６７Ｄ 出生 What should I do next? 1985-03-12` came back `answered_by: model` with `REMOTE_NOTICE` on both `/chat` and `/chat/stream`. The mock OpenRouter received the full text unchanged in 2 chat requests. This breaks owner condition (4): every chat-history message sent externally must be inside the approved synthetic boundary. It also defeats the stated purpose of the screen. A Chinese name pasted by mistake is a realistic Singapore case. The suite has no Unicode, date, UUID or digit-splitting test (the three refusal questions are all ASCII). Expected fix (not applied): NFKC-normalise, then refuse any letter or digit character that the token pattern does not cover. Strip times and ids only where the service inserts them (system case facts), not from user or assistant text. Do not let free short digits split identifiers. Add adversarial tests for each class. |
| F-2 | Medium (docs, false-assurance) | `docs/decisions/DECISION_LOG.md:1276,1281-1283`; `docs/integration/AI_MODEL_CONFIGURATION.md:128`; `apps/assistant/README.md` D-094 section; `docs/PROJECT_STATE.md` D-094 "Open" | These say every word of the question and history is screened and that the screen "refuses names, identifiers and other unknown words". F-1 shows that non-Latin text, full-width forms, dates and ids are not screened. Names built from vocabulary words are not refused either: common Singapore surnames `tan`, `lee`, `lim`, `ng` and `koh` are in the conversation vocabulary, so `Is Ryan Tan the director at 18 Garden Walk?` passes. After the F-1 fix, the known limit should state truthfully what is and is not screened. |
| F-3 | Medium | `apps/assistant/ai_assistant/remote_test.py:282-312,314-325,353-355` | **`RemoteTestModel.stream` runs blocking work on the event loop.** `stream()` calls the synchronous `_ready()` inside the async generator. `_ready()` can (i) run a whole preflight (two public GETs with 20 s timeouts, a key GET and earlier-call verification), (ii) run `verify_earlier_calls` itself (up to 25 × 5 s metadata wait per unverified call), and (iii) wait on `self._lock` while the background verifier holds it during that same wait of up to 2 minutes. `/chat/stream` serves the RM panel, so a second question asked within about 15–120 s of the first (the observed metadata lag) can freeze the whole assistant process, including health, model admin and other users. `BudgetedChatModel.stream` deliberately moves its own blocking work off the loop with `anyio.to_thread.run_sync`, so this breaks the existing pattern. Reproduced: with a `fetch` that takes 1 s, a 10 ms asyncio ticker running beside `model.stream()` stalled for **2.02 s**. Fix direction: `await anyio.to_thread.run_sync(self._ready)` in `stream`, and do not hold the lock across the metadata wait (or bound the wait inside a request). Fail-closed safety is not affected. |
| F-4 | Medium (test reliability / evidence) | `apps/assistant/tests/test_remote_test.py:452-453` | **The main journey test is flaky.** `test_hr_activates_gpt_oss_and_the_rm_chat_uses_it_then_rolls_back` asserts all 4 ledger rows are `verified` straight after the streamed RM call. That call's verification runs on the daemon `remote-verification` thread, and unlike the failure/provider tests this test does not join it. Observed **4 failures in 6 runs** of the file (`At index 3 diff: 'unverified' != 'verified'`), plus 2 clean runs. The implementer's "34 passed" is therefore not reproducible on demand. Join the verification thread (as the other tests do) or build the journey with `background=False`. |
| F-5 | Low | `apps/assistant/scripts/build_synthetic_boundary.py:199-201`; `synthetic_boundary.json` `system_vocabulary` | The system vocabulary is every string-constant token in assistant **and backend** code. It therefore includes third-party identifiers from backend fixtures and tests-in-app: `opq`, `201511222d` (the OPQ PTE. LTD. UEN, which the test itself calls `real`), `sim`, `pte`, `ltd`, `holdings`, and 46 id-like tokens such as `199801111h`, `s2222222e` and `s9988776f`. Free-text case facts that are not in `data_values` are screened only against this vocabulary: `steps[].result`, `blockers[].app_explanation`, `what_is_needed`, `timeline[].what`, `readiness.blockers/warnings` and `system_problem.message`. Low because the entity, document and value checks must already pass for GARDEN BUSINESS. Recommend excluding identifier-shaped tokens (3+ digits, UEN/NRIC shapes) and other companies' names from `system_vocabulary`. |
| F-6 | Low | `apps/assistant/ai_assistant/remote_test.py:22,257,287-289`; `AI_MODEL_CONFIGURATION.md:133`; `DECISION_LOG.md` T3 | **The call limit is per model instance, not per process, and only closed calls count.** `_start_call` is taken when `RemoteTestModel` is built. A new model is built on every activation and every restore (`_build_stored`), which resets the count. In-flight calls are not counted, so with `max_in_flight=1` two requests that both pass `_ready` before either closes can overshoot by one. Closed calls from another process on the same ledger (for example a re-qualification) also count. The ledger cap still bounds the money. Fix the wording or count per process (and count reservations). |
| F-7 | Low (docs) | `docs/integration/AI_MODEL_CONFIGURATION.md:94` | The new `## 9.` section sits between `## 5.` and `## 6.`, so the headings go 5, 9, 6, 7, 8. Move it after section 8 or renumber. |
| A-1 | Advisory | `apps/assistant/ai_assistant/main.py` `remote_gate`; `remote_test.py:222,367-368` | The boundary is enforced in `main.py` through a duck-typed marker (`requires_synthetic_boundary`), not inside `RemoteTestModel`. A future wrapper that hides the attribute, or a new caller, would skip the boundary without any error. Today the only other caller, the qualification harness, uses fixture cases plus repository guidance and the synthetic seed only (verified in `Workspace`), so this is not a current defect. |
| A-2 | Advisory | `apps/assistant/assistant_eval/live.py` | The edited working copy is LF while the other files are CRLF (autocrlf=true). Git warns about it, but the HEAD blob is LF and `diff --stat` equals `--ignore-cr-at-eol`, so no blob churn results. |

## Owner requirements - verification

| Requirement | Result | Evidence |
| --- | --- | --- |
| Default off; no D-094 means behaviour as at `c36b8af` | Verified | `_remote_entries` returns the same `pending_authorisation`/`REMOTE_NOT_AUTHORISED` entry, field for field. `entry_for` refuses non-selectable entries. `remote_gate` returns `(active.model, None)` for a non-remote model, so `/chat` and `/chat/stream` take the original paths (notices unchanged). A stored code-profile activation without D-094 reverts with `PROFILE_UNAVAILABLE`. Tests `test_the_mode_is_off_by_default…` and `test_without_the_decision…` pass. |
| (1) D-094 authorisation, (2) development environment, (5) provider/endpoint/credential/budget checks | Verified | `readiness()` checks the decision, the D-091/D-092 interlock, a literal-loopback backend, local http origins, the attestations, the approved endpoint and the reasoning settings. The preflight is the unchanged Phase B `run_preflight`. Each call: cached preflight, verification of earlier calls, breaker check, and per-call verification afterwards. Refusals raise `budget_refused` and the RM gets the case-data answer. |
| (3) case verified server-side from the backend snapshot | Verified | `check()` reads `snapshot.summary.case.entity` (fetched with the RM's session), the documents and the facts. Nothing from the browser is used apart from the question and history. |
| (4) every value, knowledge item and history message sent is inside the boundary | **Not met (F-1)** | Values, documents, viewer and knowledge: verified. Message text: bypassable. |
| (6) explicit HR activation | Verified | Uses the D-093 flow: connection test = preflight; qualification = counted manifest, G-8, NOT_SCORED; activation needs a passing qualification on the current fingerprint and basis, a passing preflight probe and the acknowledgement. |
| Existing ChatModel, selector, chat and stream routes; no separate page | Verified | No route, page or component was added. The frontend changes only `AiModelManagement`, and the frontend has no D-094/OpenRouter text outside that page. No trace of the earlier standalone test page remains (grep of frontend `src`, backend `app`, assistant `ai_assistant`, docs and scripts). |
| Exact-line validation and guardrails unchanged; HR/RM separation | Verified | `validate_answer`/`StreamingGuard` paths are unchanged. `lead_notice` is only prepended to the notices. The admin router is unchanged apart from the code-entry branches. |
| Key server-side only | Verified | Read from the process environment by the existing factory. `test_qualification_needs_the_manifest_and_the_key_never_leaves_the_server` passes. No secret patterns in the new files. |
| Show active model and model vs fallback | Verified | `REMOTE_NOTICE` on model answers. `REMOTE_BOUNDARY_NOTICE` plus a closed reason code on refusals. `answered_by` is unchanged. Telemetry gets `remote_boundary`. |
| Earlier qualifications invalidated | Verified | `BASIS_FILES` gains `remote_test.py`, `remote_checks.py`, `synthetic_boundary.py`/`.json`, and `BASIS_FIXTURES` gains `phase_b_questions.json`. |
| Service opens the live gate only in `remote_test.py` | Verified | `test_the_service_never_opens_the_live_gate` passes with exactly `ai_assistant/remote_test.py` and `scripts/evaluate_answers.py`. `main.py` has no `allow_live_network`. |
| Refactor `live.py` → `remote_checks.py` unchanged | Verified | AST comparison: all 22 moved definitions and constants are identical. `live.py` keeps only `recheck_quarantined`, `LiveMonitor` and `write_artifacts` and re-exports the rest. `evaluate_answers._preflight` → `run_preflight` is step-for-step equivalent (same order, same early returns, `fetch=live.fetch_public` resolved at call time). |
| D-091/D-093 intact; D-092 not treated as accepted | Verified | The D-094 entry says D-092 is "**not** accepted (still PROPOSED)" and D-091 and D-093 are unchanged apart from T3. The D-091, D-092 and D-093 headings are unchanged. |
| No paid call before owner authorisation | Verified for this candidate | No real network was used in any check I ran (mock transports and a fake listing). T7 is a process control: nothing in the code stops a configured paid qualification. That is consistent with the directive. |

## Checks run (this session, on the frozen content)

| Check | Result |
| --- | --- |
| Content ID start / end | start matches the brief; end: identical `b3f96317…ba031` |
| `tests/test_remote_test.py` ×6 (one combined with others) | 34 tests; the journey test failed in 4 of 6 runs (F-4); every other test passed in every run |
| `tests/test_remote_test.py test_phase_b_live.py test_openrouter_adapter.py test_model_management.py` | 1 failure only (the F-4 flake); all else passed |
| Full assistant suite (`-p no:cacheprovider`, `-B`) | 2409 collected, 2395 passed, 14 failed (all `OSError: [Errno 24] Too many open files`, in test_model_factory, test_phase_b_live, test_required_p2 and test_streaming_resources); those 4 files in isolation: 288 passed. The F-4 journey test passed in this run (it is intermittent) |
| ruff check / ruff format --check (`--no-cache`) | All checks passed; 110 files already formatted |
| mypy (cache in scratch) `ai_assistant assistant_eval scripts tests/test_remote_test.py` | Success: no issues in 59 source files |
| Frontend `npx tsc -b --pretty false` | exit 0 |
| Frontend vitest `AiModelManagement.test.tsx` | 13/13 passed |
| Frontend vitest the 6 AI-assistant files (`aiAssistant*.test.ts`, `AiAssistantPanel`, `aiAssistantContext`, `aiAssistantText`) | 76/76 passed |
| `check_project_state`, `check_architecture`, `check_policy_authority`, `check_secrets`, `check_external_provider_readiness`, `check_tooling_config` | all PASS |
| `git diff --check c36b8af` | clean |
| Untracked/new-file whitespace (trailing whitespace, final newline) | clean on all 6 new files and all 18 modified files |
| `diff --stat` vs `--ignore-cr-at-eol` | identical (18 files, +694/−477) |
| Adversarial probes (scratch, outside the repo) | F-1 boundary bypasses (direct and end to end, both routes); F-3 event-loop stall 2.02 s |

Probes are in
`C:\Users\shane\AppData\Local\Temp\claude\C--Users-shane--claude-spares-spare-6YcPey\583f9cb6-22ae-4b09-9725-20ab186f8738\scratchpad\qg094\`
(`probe_boundary.py`, `test_probe_journey.py`, `test_probe_loop.py`). No real OpenRouter, no
non-loopback host, no `.env`, no Mongo.

## Not evidenced (carried, not a finding)

- No real CLM backend Garden case was run through the boundary (fixture snapshots only).
- No real provider call (correctly, pending owner authorisation of manifest, calls and cap).

## Readiness

Not ready for publication. Bounded remediation of F-1 to F-4 is needed (F-5 to F-7 are
recommended), followed by a fresh independent QG of the changed delta. Unchanged verified
evidence above may be reused: refactor equivalence, default-off, docs status, checkers. No
commit, push or PR is authorised, and none was made.
