# AI Assistant Phase A1 — Implementation and Stage 2 Acceptance Handoff

| Item | Value |
|---|---|
| Date | 2026-10-26 |
| Authority | Owner authorisation for Phase A1 (WP1 + WP2); planner `.ai-pipeline/001_planner/AI_ASSISTANT_PHASE_A_PLAN.md` (decisions A-1, A-3, A-6, A-7 recorded there) |
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\assistant-phase-a1-20261026` |
| Branch | `feat/assistant-phase-a1-20261026` (no upstream set; not pushed at time of writing) |
| `BASE_SHA` = `origin/main` at start | `1d039865bf5197a76add7f733128829bb05019ac` (fetched 2026-10-26) |
| Candidate commit / tree | `d86015384b62c56c98739e6348b32cb0b4f15c24` / `f17e645cc1389f7d19ea7b07814d927c4d6038ff` |
| Change classes | `AUTH_RBAC_SECURITY` (logging), `ARCHITECTURE_REFACTOR` (new seams, dev-only package), `CI_TOOLING` (repository script), `DOCS_ONLY` |
| Remote model calls / OpenRouter calls / spend | none / none / US$0.00 |

## 1. What changed

### WP1 — content-free observability

| File | Change |
|---|---|
| `apps/assistant/ai_assistant/telemetry.py` (new) | `AnswerMetrics` with validation of every field (counts, timings, closed codes, 16/32-hex ids, model-name pattern); `RetrievedEntry` / `RetrievalMetrics` with opaque `entry_ref` (SHA-256 prefix of the entry id); `NullSink`, `MemorySink`, `LogSink`; `MetricsRecorder` (builds only when a sink is in use; drops and counts failures; never logs an error that could quote a value); `prompt_version()` (hash of the prompt builder source, rules and page terms); `describe_messages()` (characters per prompt part) |
| `apps/assistant/ai_assistant/main.py` | `create_app(metrics=, on_prepared=)`; `_Outcome` per answer; retrieval timing in `prepare`; one `emit` per `/chat` and `/chat/stream` request (small talk, fallbacks, partial streams and client disconnects included). Response construction and control flow are unchanged |
| `apps/assistant/ai_assistant/config.py` | `telemetry: Literal["off", "log"] = "off"` |
| `apps/assistant/tests/test_telemetry.py` (new) | 50 tests (section 3) |

Fields per record (owner decision A-3 applied): `metrics_version`, `request_id`, `route`,
`answered_by`, `fallback_reason`, `model`, `prompt_version`, `part_chars{rules, facts, history,
knowledge, terms, question, other}`, `message_count`, `history_turns`,
`retrieval{confidence, degraded, entries[{kind, ref, version, score, fallback}]}`,
`allowed_catalog_lines`, `allowed_knowledge_lines`, `kept_lines`, `left_out_lines`,
`cited_sources`, `cut_short`, `cancelled`, `timings_ms{retrieval, first_model_piece,
first_displayed_line, total}`. **No `case_id`, no facts hash**, no text of any kind.

### WP2 — offline evaluation harness

| File | Responsibility |
|---|---|
| `apps/assistant/assistant_eval/scenarios.py` | Strict scenario schema and loader |
| `apps/assistant/assistant_eval/variants.py` | Six documented synthetic variants over the saved Garden fixtures (`no_documents`, `completed`, `no_action_for_viewer`, `technical_failure`, `goldtier_uncertain`, `instruction_in_document_value`); pure, deep-copying |
| `apps/assistant/assistant_eval/snapshot.py` | Stable line ids (`C-` catalog text hash; `K-` entry id + version + sentence hash, independent of the `[Gn]` tag), prompt fingerprint without history, compact deterministic JSON |
| `apps/assistant/assistant_eval/gold.py` | Gold schema with coherence rules, stub writer (keeps owner labels), lock/verify, synthetic self-test gold (fixed rule, labelled as such) |
| `apps/assistant/assistant_eval/models.py` | Self-test selectors (perfect, random, prose, injection, empty) and `local_model` (literal loopback only; refused when a proxy variable is set) |
| `apps/assistant/assistant_eval/runner.py` | Drives the real `create_app` on `/chat/stream` with a mock CLM transport, a temporary knowledge base (fixed store clock), embeddings off, code-default settings (`model_construct`, environment and `.env` ignored); per-turn drift detection against frozen snapshots |
| `apps/assistant/assistant_eval/scoring.py` | Deterministic label-free and gold-based measures; result kinds `EVALUATOR_SELF_TEST`, `MODEL_RUN_UNLABELLED`, `MODEL_EVALUATION` |
| `apps/assistant/assistant_eval/report.py` | JSON + Markdown, banner first |
| `apps/assistant/scripts/evaluate_answers.py` | CLI: `check`, `snapshot`, `stubs`, `worksheet`, `lock`, `run` |
| `apps/assistant/tests/fixtures/eval/scenarios.json` | 16 single-question scenarios × 4 questions, 5 four-turn conversations, 5 adversarial scenarios, 3 consistency pairs |
| `apps/assistant/tests/fixtures/eval/snapshots.json` | 84 frozen turns, 73 distinct allowed lines (166 lines, 208 KB) |
| `apps/assistant/tests/fixtures/eval/gold.json` | **Stubs only**: 84 turns, 0 labelled (A-6) |
| `apps/assistant/tests/test_eval_harness.py` | 30 tests (section 4) |

### Documentation

`apps/assistant/README.md` (Observability; Offline evaluation; test commands),
`apps/assistant/.env.example` (`AI_ASSISTANT_TELEMETRY=off`), `docs/ARCHITECTURE.md`
(dated A1 entry, 16 lines; the file's mixed CRLF/LF line endings were preserved byte for
byte), the Phase A planner (A1 decisions recorded) and the investigation report.

## 2. Behaviour, contracts and invariants

| Question | Answer | Evidence |
|---|---|---|
| API routes / request or response schemas / status codes / notice strings | Unchanged | No model or route edits; `test_answers_are_byte_identical_with_and_without_metrics`, `test_a_failing_sink_never_changes_the_answer` |
| Model request | Unchanged (`llm.py` untouched) | `test_the_model_is_sent_the_same_messages_with_metrics_on`; `git diff 1d03986 -- apps/assistant/ai_assistant/llm.py` empty |
| Output guard, catalog, prompts, retrieval | Unchanged (`guardrails.py`, `prompts.py`, `knowledge/*` untouched) | `git diff --stat` |
| Deterministic fallback semantics | Unchanged | full existing suite (section 3) |
| Business use cases, UI, frontend | Unchanged (no frontend file changed) | `git diff --stat`; frontend tests (section 3) |
| Configuration | One new setting, default `off` | `config.py` |
| Persistence | None added (metrics go to a sink; harness output to git-ignored `data/eval/` or a chosen folder) | — |
| Security / auth | No auth change; telemetry content-free by validation; harness model path loopback-only | tests below |
| External provider / provider status | None | — |
| Architecture | New owner of per-answer metrics (`telemetry.py`), two `create_app` injection seams never set from settings, a dev-only package `assistant_eval` that `ai_assistant` never imports | `test_the_runtime_package_never_imports_the_harness`; ARCHITECTURE entry |

## 3. Verification evidence (candidate tree `f17e645`)

| Check | Command (from `apps/assistant` unless stated; repo `.venv`; `PYTHONPATH` pinned to the worktree) | Result |
|---|---|---|
| Baseline assistant suite on `1d03986` (before any change) | `python -m pytest --junitxml=…` | 1,190 tests: 1,183 passed, **7 failed** — all `OSError: [Errno 24] Too many open files` in `test_streaming_resources.py` (`test_loopback_total_deadline[*]` ×5, `test_real_chunked_http_enforces_budgets[oversized, many-frames]`); the same file alone: **80 passed** |
| Full assistant suite on candidate | same | 1,270 tests: **1,263 passed, the same 7 environment failures**, 0 skipped, 161 s; `test_streaming_resources.py` alone: **80 passed** |
| New tests | `pytest tests/test_telemetry.py tests/test_eval_harness.py` | **80 passed** (50 + 30) after the final snapshot format change |
| Ruff | `ruff check ai_assistant assistant_eval tests scripts`; `ruff format --check …` | pass; 76 files formatted |
| mypy (strict) | `mypy ai_assistant assistant_eval`; `mypy scripts/evaluate_answers.py` | no issues (36 + 1 files) |
| Backend integration | `apps/backend`: `pytest tests/test_ai_assistant_main_integration.py` | **2 passed** (`mock`, `sandbox`) |
| Frontend assistant tests | `apps/frontend`: `npx vitest run` on the 7 assistant test files | **7 files, 87 tests passed** (`node_modules` linked by a junction to the primary checkout's identical lockfile install; git-ignored) |
| Assistant E2E | `apps/frontend`: `CLM_E2E_BACKEND_ORIGIN=http://127.0.0.1:8999 npx playwright test e2e/assistant-streaming.e2e.ts` | **1 passed**. The variable is only parsed by the test's network policy (`allowDirectBackend: false`); `run_e2e.py` normally supplies it |
| Secret scan | `python scripts/check_secrets.py` (repo root) | pass (before commit; rerun in pre-PR) |
| Architecture / project state | `python scripts/check_architecture.py`; `python scripts/check_project_state.py` | PASS / PASS |
| Whitespace | `git diff --check`; trailing-space, tab and final-newline scan of every new file | clean |
| Snapshot currency | `python scripts/evaluate_answers.py check` | current (84 turns, sha256 `c931f58eec30c8b2…`) |
| `pre_pr_check.py` | — | NOT RUN YET (runs after the gate, on the committed integrated state) |
| Hosted CI | — | NOT EXECUTED (assistant tests are not in `ci.yml`; hosted CI has been billing-blocked) |

### Observability privacy evidence

`test_no_case_user_or_model_content_reaches_a_record` plants 12 sentinels (company name, UEN,
street, document value, viewer name, question, history, model reply, knowledge title, body
and entry id, timeline message) and checks that none, nor an allowed-line text, the case id,
user ids, team id or a raw `guidance.`/`resolution.` id, appears in any record from
`MemorySink` or `LogSink` across `/chat`, `/chat/stream` and small talk. Field validation
refuses 15 non-content-free values and 6 bad retrieval entries without quoting them
(`test_a_value_that_is_not_content_free_is_refused_without_quoting_it`,
`test_retrieval_identifiers_must_be_content_free`). With telemetry off, no record is built
(`test_telemetry_is_off_by_default_and_builds_nothing`). A client disconnect mid-stream is
recorded as `cancelled` (`test_a_client_that_disconnects_mid_stream_is_recorded_as_cancelled`,
raw ASGI with an `http.disconnect`).

### Evaluator self-test results (E0) — NOT model results

All runs: 84 questions, embeddings off, synthetic self-test gold (fixed rule), result kind
`EVALUATOR_SELF_TEST`.

| Self-test selector | Line validity | Fallback rate | Unsafe display | F1 (micro) | Notes |
|---|---|---|---|---|---|
| perfect (gold lines) | 1.0 | 0.0 | 0 | 1.0 | primary hit 1.0; consistency 1.0 |
| random (seed 7, 2 reps) | 1.0 | 0.0 | 0 | 0.0786 | stability 0.058; reproducible for the seed |
| free prose | 0.0 | 1.0 (`policy_no_allowed_line`) | 0 | — | nothing shown |
| injected instruction + 1 allowed line | 0.2 | 0.0 | 0 | 0.667 | the 4 injected lines never shown |

These show the scorer and guards behave as their rules predict. They say nothing about
Ministral, GPT-OSS or any other model.

## 4. WP2 tests

Scenario coverage; variants as described and never mutating the saved fixtures; committed
snapshots and stubs fit the scenarios (all stubs, kind `owner`, no lock file); snapshot
determinism; **a snapshot equals what the model was actually sent** (fingerprint and tagged
knowledge lines, every one of 84 turns); line ids independent of tags; E0 ×4; unlabelled
model run has no quality score; stub/self-test gold cannot be locked; owner-gold lock
round-trip and tamper refusal (in-memory, test-only labels); six incoherent gold-turn shapes
refused; gold naming unoffered lines refused; drift flagged and excluded; five non-loopback
URLs refused; proxy variables refused; runtime never imports the harness; reports start
with their kind. A module-wide socket guard fails any non-loopback connection attempt.

## 5. Deviations from the plan

1. **A-3 restrictions applied:** no `case_id`, no facts hash.
2. `finish_reason`, `empty_content`, `usage` and `budget` fields are omitted: they need the
   adapter (WP3/WP4, A2 scope). `metrics_version` 1 leaves room to add them.
3. Backend-load time is not measured (the case is loaded by a FastAPI dependency before the
   handler). `first_displayed_line` is the first streamed line, or the final answer when no
   line streamed; it is `null` on `/chat`.
4. `prompts.py` is untouched: `prompt_version()` and `describe_messages()` live in
   `telemetry.py` (smaller overlap with in-flight assistant branches, below).
5. `assistant_eval` is not added to setuptools package discovery: it is a dev-only tree like
   `tests/` and `scripts/` (no packaging change); the README's mypy command includes it.
6. The committed snapshots are not compared to a fresh build in the unit tests (that would
   fail every unrelated prompt change); `evaluate_answers.py check` and per-run drift flags
   do it, and drifted questions are excluded from gold scores.
7. Owner gold labels do not exist (A-6); E1 (local model baseline) is deferred (A-7). The
   labelling worksheet is generated on demand into `data/eval/` (not tracked).
8. The retriever's recency score uses the wall clock while the store clock is fixed, so
   retrieval scores decay slowly over months; `check` reports any resulting drift.
9. Correction to the investigation report's section 5.2: the waiting-for-documents fixture
   was measured with the address case's documents attached; the repository tests (and the
   snapshots) pair it with no documents (facts 3,307 characters, not 4,605).

## 6. Risks and coordination

- Two unmerged teammate branches change the same assistant files:
  `origin/feat/ai-assistant-answer-records` (`main.py` +206, `config.py`, `store.py`,
  `knowledge_api.py`, D-084 answer records) and `origin/feat/ai-assistant-explanations`
  (`prompts.py` +213, `guardrails.py` +253, `main.py` +17; labelled "D-085, proposed", a
  number main already uses). Whichever lands second must resolve conflicts in `main.py` and
  `config.py`; a prompt or catalog change also changes `prompt_version` and makes the frozen
  snapshots drift (`check`), so snapshots and any owner labels must then be refreshed and
  reviewed.
- `on_prepared` exposes case facts and the prompt in-process. It is harness-only, never set
  from settings; documented in `create_app` and the README.
- `LogSink()` attaches a standard-error handler to the `ai_assistant.metrics` logger (with
  propagation off) when that logger has none.
- The 7 full-suite failures are a pre-existing Windows file-descriptor limit, present on
  the untouched baseline.

## 7. Credential note (owner message during A1)

An OpenRouter key was provisioned as `OPENROUTER_API_KEY` (workspace `FYP - AI Assistant`,
key `CLM - AI Assistant`). Without reading or printing its value and without any network
request:

- Presence in this session's process, user and machine environment scopes: **MISSING**
  (it may be set only in another terminal or in a `.env` file; `.env` files were not
  opened, per `AGENTS.md`).
- The existing settings loader **does not recognise** `OPENROUTER_API_KEY`: it reads only
  `AI_ASSISTANT_*` variables (`env_prefix`), so the key cannot reach today's model requests
  (verified with a dummy value in a separate process). No code in this branch references it.
- No OpenRouter profile exists in A1; any mapping of `OPENROUTER_API_KEY` belongs to A2 (WP3)
  and needs the A2 authorisation.

The mismatch is recorded as A2 follow-up **F-A2-1** in the planner and in
`AI_ASSISTANT_PHASE_A1_TOKEN_BREAKDOWN.md` section 5.

## 8. Token breakdown (owner direction during A1)

`.ai-pipeline/reports/AI_ASSISTANT_PHASE_A1_TOKEN_BREAKDOWN.md` gives the offline context
breakdown from the frozen snapshots and harness telemetry (exact characters; approximate
tokens), hypothetical GPT-OSS 120B per-request costs at economical, typical and
conservative 2026-10-26 prices (not re-fetched), and unimplemented optimisation
opportunities. It is analysis only; it changes no code.

## 9. Next action

Independent Quality Gate on the branch head (product commit `d860153`, tree `f17e645`, plus
the documentation commit with these reports); then latest-main integration,
`pre_pr_check.py` on the committed state, and A1 publication as a separate PR (never merged
by the implementer). A2 is not started.
