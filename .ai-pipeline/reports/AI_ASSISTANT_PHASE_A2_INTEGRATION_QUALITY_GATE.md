# AI Assistant Phase A2: independent latest-main integration Quality Gate (PR #116)

| Item | Value |
|---|---|
| Date | 2026-10-26 |
| Gate | Stage 3: independent, delta-focused integration re-QG (`fyp-quality-gate`) |
| Verdict | **PASS** (one Low and two Informational findings; none required. R2-1 Low carried forward) |
| Reviewed commit | `65c6cfa0aa7d2ab901e3d724d96ed26a24dcb529` (merge), tree `e48fac1da5cf1ce9b6e4626b776719975366f5dc` |
| Branch | `feat/assistant-phase-a2-20261026-int`. The merge is local only; the remote is still at `c5b5f8a` |
| Parent 1 | `c5b5f8aeb6f14ca67e547cf4fc6a7a8ecd5b29b0`: the reviewed A2 product `e0d45d4` (tree `859ec51a`, re-QG R2 PASS) plus QG reports only (3 files under `.ai-pipeline/reports/`, +810 lines) |
| Parent 2 | `06e6a9b81b59f631ddbcf5136cee9f1bf384df10`: `origin/main` as a local ref (not fetched), PR #114 (D-090) |
| Merge base | `7d6a31aa196cff23c0b5b1fd4e5e31cf9bce0efc` (PR #113) |
| Worktree | clean at start and at end (`git status --porcelain` empty); HEAD, tree and parents matched the assignment |
| Reviewer | independent: did not write this merge, the A2 product or PR #114 |
| Remote activity / spend | none. No non-loopback request, `OPENROUTER_API_KEY` unset for every run and never read, `.env` not opened, US$0 |

## 1. Scope and provenance of the merged tree

I checked where every file's blob comes from. Paths are relative to the merge base `7d6a31a`.

| Set | Files | Result |
|---|---|---|
| A2-only delta (`7d6a31a..c5b5f8a`, not touched by main) | 26 | Equal to `c5b5f8a`, except the two integration test edits (section 4) |
| Main-only delta (`7d6a31a..06e6a9b`, not touched by A2) | 30 | All equal to `06e6a9b` |
| Shared | 5 | See section 2 |
| Changed relative to **both** parents | 7 | the 5 shared files plus `test_budget_guard.py` and `test_openrouter_adapter.py`. Nothing else |
| `apps/backend`, `apps/frontend` vs `06e6a9b` | 0 | No difference. Backend and frontend are main's content exactly |
| A2 product modules vs `e0d45d4` (`budget.py`, `model_factory.py`, `model_profiles.py`, `openrouter.py`, `config.py`, `llm.py`, `telemetry.py`) | 7 | All byte-identical to the reviewed content |
| Eval fixtures `gold.json`, `snapshots.json` | 2 | Blobs equal to main's (`1e37912e…`, `e5a726d0…`) |

## 2. Conflict and auto-merge review

**Method.** I re-ran the three-way merge myself for each shared file (`git merge-file` with base `7d6a31a`, ours `c5b5f8a`, theirs `06e6a9b`) and compared the result with the committed blob.

| File | Re-merge | Resolution review | Verdict |
|---|---|---|---|
| `apps/assistant/README.md` | clean, **identical** to the merge | Both deltas are present: A2's "Model profiles and budget guard" section, and main's redaction wording for answer records. Line count 492 = base 447 + A2 45 + main ±2 | OK |
| `docs/ARCHITECTURE.md` | clean, **identical** to the merge | Both deltas are present: A2's candidate entry, and main's two answer-record paragraphs | OK |
| `apps/assistant/ai_assistant/main.py` | 1 conflict, in the import block only. Every other hunk is identical to the clean auto-merge | The resolution is a union: A2's multi-line `from .llm import (...)` plus `from .model_factory import build_chat_model`, and main's `from .prompts import TopicPlan, build_messages, prefix_messages, topic_plan`. No duplicate or dropped name. Line count 889 = 781 + 70 + 38. ruff and mypy are clean | OK |
| `docs/decisions/DECISION_LOG.md` | 1 conflict: both sides append at the end of the file | Main's D-090 block comes first, then A2's D-091 block. Both are verbatim except one sentence in D-091 (line 1140): "reserved by PR #114" became "PR #114's, merged before this one", which is accurate after the merge. Nothing is removed. Line count 1165 = 1108 + 25 + 32. CRLF throughout, same as both parents | OK |
| `docs/decisions/ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md` | 1 conflict: both sides append at the end of the file | Amendment 2 (D-090, main) comes first, then Amendment 3 (D-091, A2). Both are verbatim except the same sentence change (line 648). Line count 670 = 505 + 137 + 28. CRLF throughout | OK |

Other checks on the resolution:
- No conflict markers anywhere in the tree.
- `git diff --check` is clean against both parents.
- The merge adds no untracked Markdown, so there is no extra whitespace lane.
- **Numbering:** among all local refs (`refs/heads`, `refs/remotes`, not fetched), only this branch defines D-091 or "Amendment 3", so plan step 12.3.9 holds locally.
- The words "reserved by/for PR #114" survive only in the historical A2 QG reports R1 and R2, which is correct for those reports.

## 3. Semantic review: A2 × PR #114 in `main.py`

| Interaction | Evidence | Result |
|---|---|---|
| `_model_reply` / `with_required_lines` vs A2's `_Outcome` | Both paths call `outcome.selected(validation)` (`main.py:642`, `:731`) on the guard's own validation **before** `_model_reply` (`main.py:310`) adds required lines. So `kept_lines` / `left_out_lines` count only model-selected lines. A2's `reported()` / `failed()` record only usage, finish reason, budget and error class; they never touch lines | Required lines are not credited to the model |
| Executed check of the line above | My scratch probe (section 6, P-1) runs through the dormant remote profile with mock transport only. Stream and chat both gave answers of 2 lines with `added_lines == [0]`; the only non-added position is the model's `ALLOWED` line; `kept_lines == 1` in both metrics records; `fallback_reason == "none"`; no answer line appears in `record.to_json()` | PASS |
| `streamed` tracking in the stream loop | Main's `streamed = shown` sits inside the `if shown is not None` branch. A2's `outcome.reported(piece)` runs before `guard.feed`, and A2's `empty_content` assignment comes after the loop. The two share no state. `streamed=` is passed on both the normal path and the `stream_partial` path | No interference |
| `record_reason` | A2 adds `budget_refused` → `"model_unavailable"` (`main.py:258`). The `FallbackReason` literal in `answer_records.py` (main's content) still contains `model_unavailable`. On a mid-stream failure with partial text, `stream_partial` still overrides, as reviewed in A2 | OK |
| Answer-record redaction | Main's hunks (`allowed_lines(..., redact)`, redacted `chosen_lines` and `shown_answer`) are present unchanged; A2 has no hunk there. The answer-record and redaction tests pass in the full run | OK |
| Fallback and notice contracts | A2 adds no notice. A budget refusal falls back with `FALLBACK_NOTICE` through main's unchanged `_fallback_reply`. A2's notice tests (`test_reasoning_that_uses_the_whole_limit_keeps_todays_notice` and others) pass | OK |
| Composition | `main.py:395` calls `build_chat_model(config, local_adapter=OpenAICompatibleChatModel)` with no transport and no ledger. The remote profile therefore stops at L1 (`PROFILE_DORMANT`) before any credential read. `.complete` / `.stream` / `.warm` are called only at `main.py:637`, `:713` and `:679` (plus the budget wrapper), so PR #114 adds no new model call site. Warm-up keeps its `is_local_model_url` gate | OK |

## 4. Integration-only test edits

| Test | Before | After | Assessment |
|---|---|---|---|
| `test_budget_guard.py::test_a_remote_answer_is_settled_at_its_reported_cost` (`:141-143`) | `done["answer"] == ALLOWED` | `ALLOWED` is present and its position is not in `added_lines` | **Intent kept.** The settlement, ledger status, budget-metrics and usage assertions are unchanged |
| `test_openrouter_adapter.py::test_a_remote_answer_through_the_service_records_content_free_v2_metrics` (`:652-666`) | `answer == ALLOWED` for both routes; `ALLOWED not in` the telemetry JSON | Per-route presence and not-added check; **no** answer line, added ones included, may appear in the telemetry JSON | **Intent kept, and the content-free assertion is stronger** (it now covers server-added lines) |

Both edits are needed: under D-090 the service now puts the topic's required line in front of the model's line. Neither edit weakens a budget, security or telemetry assertion. The answer-shape pinning is looser than before; see finding L-1.

## 5. Findings

| ID | Severity | Location | Failure scenario | Suggested fix | Blocking |
|---|---|---|---|---|---|
| L-1 | Low (test quality) | `apps/assistant/tests/test_budget_guard.py:143`, `apps/assistant/tests/test_openrouter_adapter.py:655` | The tests no longer pin the whole answer. Suppose a later change made the remote path insert an extra line that is not reported in `added_lines`, or credit an added line to the model in `kept_lines`. These two tests would still pass. Today the behaviour is correct (probe P-1 below), and `test_explanations.py:830` pins `added_lines` on the local path | Assert that the non-added positions are exactly `{lines.index(ALLOWED)}` and that `record.kept_lines == 1`, as probe P-1 does | No. Optional; any change to reviewed content needs a fresh review |
| I-1 | Informational (docs wording) | `docs/decisions/ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md:658`, `docs/decisions/DECISION_LOG.md:1161`, `apps/assistant/README.md:424`, `docs/ARCHITECTURE.md:1022` | A2's "unchanged" statements ("Sections A and C are unchanged, including the exact-line catalog", "prompts, …, answer records … are unchanged") now follow PR #114, which changes section C, prompts and answer-record redaction. They are accurate as "not changed by A2", but a reader could take them as describing the current state | When D-091 status text is next edited, say "not changed by A2 (section C as amended by Amendment 2)" | No |
| I-2 | Informational (evidence scope) | implementer's `parity_probe.py` | The probe always injects `chat_model=` (or disables the model), so it never runs `build_chat_model` composition. Composition parity rests on `tests/test_default_request_golden.py`, which passed in my full run | None needed for this gate. A future parity probe could add a case composed through the factory with a mock transport | No |

There are no Critical, High or Medium findings, and the merge introduced no new defect.

**Carried forward, not caused by this merge:**
- **R2-1 (Low):** still open; a Phase B prerequisite.
- **Plan §12.4 scoring rule:** `runner.py` now excludes `added_lines` from model-selected lines. Recording the guard and catalog version in run manifests, and an optional content-free count of added required lines in telemetry, remain Phase B prerequisites (the plan scopes them outside A2).
- **Decision status:** D-090 and D-091 still read PROPOSED in the repository; updating the status text was not part of this integration.

## 6. Evidence

Status key:
- EXECUTED: run by me, now, on `65c6cfa`.
- REUSED: valid earlier evidence for content this merge leaves unchanged.
- NOT_EXECUTED: not run; the reason is given.
- N/A: does not apply.

| Lane | Status | Count / result | Notes |
|---|---|---|---|
| Identity: HEAD, tree, parents, clean worktree | EXECUTED | match | `git rev-parse`, `git status` |
| Per-file blob provenance (section 1) | EXECUTED | 26 + 30 + 5 files classified; 7 differ from both parents | |
| Independent three-way re-merge of the 5 shared files | EXECUTED | 2 identical; 3 conflicts reviewed | section 2 |
| `git diff --check` vs both parents; conflict-marker scan; EOL check | EXECUTED | clean; 0 markers; CRLF consistent | |
| Decision-numbering scan across local refs | EXECUTED | D-091 / Amendment 3 unique | not fetched |
| `check_secrets`, `check_project_state`, `check_architecture`, `check_tooling_config`, `check_policy_authority`, `check_external_provider_readiness` | EXECUTED | 6/6 pass | |
| `tests/test_check_secrets.py` | EXECUTED | 22/22 passed | |
| `ruff check`, `ruff format --check` (apps/assistant, `--no-cache`) | EXECUTED | pass; 94 files formatted | |
| `mypy ai_assistant assistant_eval` | EXECUTED | no issues, 41 files | |
| `evaluate_answers.py check` | EXECUTED | "snapshots are current (84 turns, sha256 1421eedb7fd536ea)" | main's fixtures; nothing regenerated; gold blob equal to main's |
| **Full assistant suite** (watchdog `timeout 1800`, `faulthandler_timeout=300`, junitxml) | EXECUTED | 2,029 collected: 2,016 passed, 13 failed, all `OSError: [Errno 24] Too many open files` | The same 13 test ids as the `e0d45d4` R2 run (no additions, no removals). Run because `main.py` is a new combination |
| Isolated rerun of the 13 Errno 24 tests | EXECUTED | 13/13 passed | Classified as a host file-handle limit, not a defect. Includes `test_model_factory::test_the_suite_guard_blocks_remote_connections` |
| Scratch probe P-1: required lines vs model credit through the remote mock path | EXECUTED | 1/1 passed (stream and chat) | `scratchpad/intqg/probe/test_intqg_required_lines_probe.py`, outside the repository |
| Default-behaviour parity vs **new** main (`parity_probe.py`, `git archive 06e6a9b`, each run in an empty scratch cwd) | EXECUTED | main `7adc179fe8ef24d3…c6864` == merge `7adc179fe8ef24d3…c6864`; 336 cases, 41 model requests | Reproduces the implementer's value |
| Parity sensitivity control (pre-merge `c5b5f8a` tree) | EXECUTED | `def72e8b1576…92bc` (differs) | The probe does detect PR #114's behaviour change |
| Backend `test_ai_assistant_main_integration.py` (mock, sandbox) | EXECUTED | 2/2 passed | Drives the merged `create_app` against the in-memory backend |
| A2 locks L1–L4, safeguards S1–S3, empty shipped registry, adapter, budget ledger | REUSED + EXECUTED | modules byte-identical to `e0d45d4` (QG, R1, R2 PASS); their tests pass in the full run | `OPENROUTER_PROFILE.endpoints == ()` re-read |
| Telemetry content-free and off by default | REUSED + EXECUTED | `telemetry` default `"off"` (`config.py:91`); `telemetry.py` identical; P-1 and the edited adapter test show no answer text in records | |
| Full backend (3,173) and frontend (1,109) suites | NOT_EXECUTED (REUSED) | n/a | `apps/backend` and `apps/frontend` are byte-identical to `06e6a9b`, and A2 changes neither. Main's own evidence for those trees applies |
| E2E (`run_e2e.py`), physical Mongo | NOT_EXECUTED | n/a | Docker and Tesseract unavailable. A2 does not touch the E2E path; `clm_poc` was not used |
| Hosted CI / remote PR state | NOT_EXECUTED | n/a | The merge is not pushed; earlier runs were billing-blocked |
| `pre_pr_check.py` | NOT_EXECUTED | n/a | Excluded by the assignment; it follows a PASS |

## 7. Evidence this merge invalidates

**Invalidated by the merge:**
- The A2 QG / R1 / R2 test results for `main.py`-dependent behaviour (prepared on the old base). Replaced by the full assistant run above.
- The implementer's pre-merge default-request parity against the old base. Replaced by parity against `06e6a9b`.
- The `e0d45d4` results of the two edited test files. Replaced; both pass in the full run.
- A2's pre-merge `evaluate_answers.py check` value. Replaced by main's fixtures, which are current.

**Still valid (REUSED):**
- A2 module reviews (locks, S1–S3, ledger, adapter, secret scanner): content unchanged.
- PR #114's own QG for its non-shared files: content unchanged.
- Backend and frontend suite evidence on main: content unchanged.

## 8. Readiness

- **Integration:** PASS for the frozen content `65c6cfa` / `e48fac1d`. The authorised next steps are `pre_pr_check.py` on this clean committed state, the reports-only commit, a normal push and the PR #116 update. These are for the coordinator, not this gate.
- **Merge:** the owner decides; hosted CI is unverified.
- **Phase B:** not authorised, and still blocked by R2-1, the §12.4 scoring prerequisites, and the absence of any approved endpoint record.
- **Live or remote inference:** none. The remote profile remains DORMANT.

## 9. Independence and write boundary

This review was independent. I made no change to the reviewed content: no edit, staging, commit, push, fetch, PR comment or merge, and `git status` was empty before and after.

My only writes were to this session's scratchpad:
- this report;
- the re-merge copies;
- `git archive` copies of `06e6a9b` and `c5b5f8a`;
- junit XML and logs;
- the probe file and parity outputs.

One side effect: the full assistant suite writes to the git-ignored knowledge store `apps/assistant/data/knowledge` under the test cwd. Main's tests already do this, and that directory existed from the implementer's runs. No tracked content changed.
