# AI Assistant Phase A1 — Independent Quality Gate

| Item | Value |
|---|---|
| Date | 2026-10-26 (checks run 02:55–03:15 UTC) |
| Role | Independent QUALITY GATE (Stage 3); did not author or remediate the reviewed content |
| Scope authority | Owner authorisation for A1 (WP1 + WP2) recorded in `.ai-pipeline/001_planner/AI_ASSISTANT_PHASE_A_PLAN.md` (A-1, A-3, A-6, A-7); WP3/WP4 (A2) not authorised |
| Worktree / branch | `C:\Users\shane\Desktop\claude-worktrees\assistant-phase-a1-20261026` / `feat/assistant-phase-a1-20261026` |
| Reviewed HEAD / tree | `7effd00a8d53df90c344fa510aeca66130cf1394` / `5a00fd2adb70e7bbc2b49710a3693ab023de0e1e` |
| Product commit / tree | `d86015384b62c56c98739e6348b32cb0b4f15c24` / `f17e645cc1389f7d19ea7b07814d927c4d6038ff` (7effd00 adds only the two A1 reports and the planner F-A2-1 note) |
| Base = `origin/main` at review | `1d039865bf5197a76add7f733128829bb05019ac` (merge-base identical; no integration drift) |
| Reviewed path set | 25 files, +6,483/−45: planner, investigation report, A1 implementation report, A1 token breakdown, `apps/assistant/{.env.example, README.md, ai_assistant/config.py, ai_assistant/main.py, ai_assistant/telemetry.py, assistant_eval/*.py (9), scripts/evaluate_answers.py, tests/fixtures/eval/{gold,scenarios,snapshots}.json, tests/test_eval_harness.py, tests/test_telemetry.py}`, `docs/ARCHITECTURE.md` |
| Change classes | `AUTH_RBAC_SECURITY` (logging/redaction), `ARCHITECTURE_REFACTOR` (new seams, dev-only package), `CI_TOOLING` (repository script), `DOCS_ONLY` |

## 1. Executive Result

**FAIL** (narrow; one blocking finding).

WP1 (content-free observability) is verified: off by default, strict validated allow-list, no
case id or facts hash, sentinel privacy test present and passing, and **byte-identical answers
and model requests versus base `1d03986`** with telemetry off, on, and with a failing sink
(independent differential probe, 261 cases). Scope, secrets, A-6 and A-7 constraints are met,
and the reported Windows `Errno 24` failures were reproduced identically on the untouched base.

The blocking defect is in WP2's core property: **the frozen evaluation snapshots are not
deterministic over wall-clock time.** The harness fixes the knowledge-store clock but not the
retriever's recency clock, so `python scripts/evaluate_answers.py check` on the exact reviewed
content **fails today** (03:05 UTC, exit 1, 5 turns drifted). After one day 77/84 turns drift and
three turns (S06#0–#2) change the lines offered to the model, so they would be flagged as drifted
and excluded from gold scoring with no code change. The handoff reports `check` as "current" and
describes the effect as decaying "slowly over months" (deviation 8); both are inaccurate for the
reviewed content. This is an unverified required criterion (deterministic harness) with a
stale/false-success evidence claim, so the result cannot be PASS WITH MINOR FIXES.

Consequence: A1 returns to bounded Stage 1 remediation (F-1 only), then a fresh independent
re-QG of the corrected delta. Most evidence below remains reusable (section 8).

## 2. Phase Acceptance Checklist

| # | Criterion (owner authorisation / planner) | Result | Direct evidence |
|---|---|---|---|
| 1 | WP1 implemented with docs and tests | VERIFIED | `telemetry.py`, `main.py` seams, `config.py` `telemetry="off"`, README "Observability", 50 tests pass |
| 2 | WP2 deterministic offline evaluation harness with docs and tests | **NOT VERIFIED** | Offline: verified. Deterministic within one run: verified. Frozen snapshots reproducible over time: **fails** (F-1) |
| 3 | Zero OpenRouter expenditure; zero remote-model calls | VERIFIED | No remote model path in code; tests use `httpx.MockTransport` and in-process selectors; `local_model` refuses non-loopback before any request (CLI probe `--base-url http://10.0.0.5:11434/v1` → `refused`, exit 2); none of my runs contacted a non-loopback host |
| 4 | No external-provider integration change | VERIFIED | `llm.py` untouched; no provider status change; `check_project_state.py` PASS |
| 5 | No WP3/WP4 work | VERIFIED | No profile, usage, budget, ledger, key mapping or OpenRouter code; `OPENROUTER_API_KEY` appears only in Markdown |
| 6 | No prompt or retrieval optimisation | VERIFIED | `prompts.py`, `guardrails.py`, `knowledge/*`, `instructions/*`, `knowledge_answers.py`, `briefing.py`, `small_talk.py`, `context.py`, `clm_client.py`, `knowledge_api.py` all unchanged (`git diff --stat` empty) |
| 7 | No change to assistant business use cases | VERIFIED | Differential parity probe: base vs candidate byte-identical (section 4.2) |
| 8 | No UI, API contract, notice-string or output-guard change | VERIFIED | No `apps/frontend` or `apps/backend` diff; parity identical for status codes (200/401/403/422), bodies, notices, NDJSON stream events, headers checked |
| 9 | Default model requests preserved byte-for-byte | VERIFIED | Real `OpenAICompatibleChatModel` with capturing transport: method, URL, all headers and JSON body identical base vs candidate for `/chat` and `/chat/stream`, telemetry off and on |
| 10 | Deterministic fallback semantics preserved | VERIFIED | Parity probe covers model down, disabled, unverifiable prose, partial stream (kept/none), cut short, small talk, knowledge on/off, history |
| 11 | No unapproved change to existing acceptance tests | VERIFIED | Only `tests/test_telemetry.py`, `tests/test_eval_harness.py` and `tests/fixtures/eval/*` added; 0 existing tests modified/removed; all 1,190 common tests have identical status base vs candidate |
| 12 | A-3: telemetry off by default; no record built | VERIFIED | `sink_for("off")` → `NullSink`; `MetricsRecorder.record` returns before `build()`; test monkeypatches `AnswerMetrics` and observes zero builds; no `LogSink`/handler created by default |
| 13 | A-3: strict allow-list; validation refuses non-content-free values without quoting | VERIFIED | `telemetry.py:80-199` (counts, closed codes, 16/32-hex patterns, exact key sets); 15 + 6 + 2 refusal tests assert the sentinel is not in the error |
| 14 | A-3: no raw `case_id`; no facts hash | VERIFIED | No such field; `git grep` finds no `facts_sha`; case id used only to route the fake backend in the harness |
| 15 | A-3: retrieval identifiers and categorisation values content-free | VERIFIED | `RetrievedEntry`: kind ∈ {guidance, resolution}, `ref` = SHA-256 prefix of entry id, version count, finite float score, bool; confidence closed set |
| 16 | A-3: sentinel privacy test; no content, secrets, customer information or model responses in records | VERIFIED | `test_no_case_user_or_model_content_reaches_a_record` (12 sentinels, both routes, small talk, `MemorySink` + `LogSink`); model name is operator configuration only (see L8) |
| 17 | A-6: gold stubs only; no manufactured authoritative labels | VERIFIED | `gold.json`: 84/84 turns `status: stub`, all empty, kind `owner`, note "STUB - NOT LABELLED"; no `gold.lock.json` |
| 18 | A-6: self-test results separated from model-performance results | VERIFIED | `result_kind` (`EVALUATOR_SELF_TEST` / `MODEL_RUN_UNLABELLED` / `MODEL_EVALUATION`), banner first in Markdown and JSON, kind in file name; stub and synthetic gold cannot be locked |
| 19 | A-7: no local model installed or used; E1 deferred | VERIFIED | `NoEmbedder`; no Ollama/model call in tests or my CLI runs; E1 not run |
| 20 | Preserve test evidence including the known Windows resource failures | VERIFIED | Independently reproduced on base and candidate (section 4.1) |
| 21 | Token breakdown: exact characters vs approximate tokens; economical and conservative pricing; prices dated, not re-fetched | VERIFIED (figures) | Every character statistic and every cost cell recomputed and matching (section 4.5). Depends on `snapshots.json`, which F-1 will regenerate |
| 22 | `OPENROUTER_API_KEY` loader mismatch recorded as A2 follow-up without touching the secret | VERIFIED | Planner F-A2-1, implementation report §7, breakdown §5; no code reference; no value anywhere |
| 23 | Optimisation opportunities identified, not implemented | VERIFIED | Breakdown §4 T1–T8; no code |
| 24 | Planner 7.3 tests 1–8 (E0 ×4, snapshot determinism, tag-independent ids, non-loopback refusal + socket guard, import boundary) | VERIFIED with caveats | All present and passing; 7.3.5 only proves same-minute determinism (F-1); socket guard gap on Windows async (L1); E0 depth (L2) |
| 25 | Implementer evidence accurate | PARTIAL | All test counts, E0 numbers, lint/type results, integration and repo checks reproduced; **snapshot currency claim stale and deviation 8 understated (F-1)** |

## 3. Contract and Integration Findings

- No API, response schema, route, status code, notice string, output guard, CLM access
  pattern or provider contract changed (criteria 4, 7–10). `create_app` gains two keyword
  seams (`metrics=`, `on_prepared=`) that default to the previous behaviour; production
  composition (`main.py:626`) passes neither, and neither is reachable from settings or env.
- `AI_ASSISTANT_TELEMETRY` is the only new setting (`Literal["off","log"]`, default `off`); an
  invalid value fails settings validation at startup (fail-closed).
- No Live/Sandbox/Mock classification, sponsor authority, decision record or project-state
  claim is changed. The planner says A1 needs no new decision; I do not require one.
- Planner deviations are reasonable but some are unlisted (L5).
- Later dependencies (not current blockers): F-A2-1 credential mapping, `usage`/`budget`/
  `finish_reason`/`empty_content`/`profile` fields and E1 all belong to A2 or later owner
  decisions.

## 4. Tester and Adversarial Findings

Environment: Windows 11, Python 3.12.10 from the primary checkout's `.venv`;
`PYTHONPATH` pinned to the worktree's `apps/assistant` (or `apps/backend`);
`PYTHONDONTWRITEBYTECODE=1`; pytest cache provider off; ruff `--no-cache`; mypy cache in my
scratch folder; `AI_ASSISTANT_KNOWLEDGE_DATA_DIR` pointed at my scratch folder so the
module-level app's default knowledge base (pre-existing import side effect) did not write into
the worktree (no test references that variable). All outputs went to my scratch folder.

### 4.1 Commands and results

| Check | Content | Result |
|---|---|---|
| `pytest tests/test_telemetry.py tests/test_eval_harness.py` | candidate | **80 passed** (50 + 30), 15.0 s |
| Full assistant suite `pytest -o faulthandler_timeout=300 --junitxml` | candidate | 1,270 collected: **1,263 passed, 7 failed**, 0 skipped, 164.7 s |
| Full assistant suite, same options | base `1d03986` (`git archive` of `apps/assistant` + `apps/frontend/src/pages` into scratch) | 1,190 collected: **1,183 passed, 7 failed**, 147.4 s |
| JUnit comparison | base vs candidate | Identical failure set (all 7 `OSError: [Errno 24] Too many open files` in `test_streaming_resources.py`: `test_loopback_total_deadline[no-newline, heartbeat, read-stall, headers-stall, chunk-header-trickle]`, `test_real_chunked_http_enforces_budgets[oversized, many-frames]`); all 1,190 common tests same status; the 80 new tests come only from the two new files |
| `pytest tests/test_streaming_resources.py` alone | candidate | **80 passed** |
| `ruff check` / `ruff format --check` (`ai_assistant assistant_eval tests scripts`) | candidate | pass / 76 files already formatted |
| `mypy ai_assistant assistant_eval`; `mypy scripts/evaluate_answers.py` (strict) | candidate | no issues in 36 / 1 source files |
| Backend `pytest tests/test_ai_assistant_main_integration.py` | candidate (`sys.path` inserts worktree `apps/assistant`) | **2 passed** (`mock`, `sandbox`) |
| `scripts/check_secrets.py`, `check_architecture.py`, `check_project_state.py` | worktree root | exit 0 / PASS / PASS |
| `git diff --check 1d03986..7effd00`; final newline and tab scan of all 19 added files | committed content | clean |
| `docs/ARCHITECTURE.md` EOL | blobs | base 1,007 CRLF + 98 LF → candidate 1,023 CRLF + 98 LF; the 16 new lines are CRLF like their neighbours; `--stat` = `--ignore-cr-at-eol` (16/0) |
| **`scripts/evaluate_answers.py check`** | candidate, 2026-10-26 03:05 UTC | **FAIL, exit 1**: "snapshots drifted: 5 turns differ (C01#1, C01#2, S02#1, S07#0, S11#1 ...)" |
| `evaluate_answers.py run --model self-test-{perfect,prose,injection}`; `self-test-random --reps 2` (out: scratch) | candidate | Match the handoff E0 table: perfect F1 1.0/validity 1.0/fallback 0/unsafe 0; prose validity 0.0/fallback 1.0 (`policy_no_allowed_line` ×84)/unsafe 0; injection validity 0.2/F1 0.6667/unsafe 0; random F1 0.0786/stability 0.0583/must-not 19/unsafe 0. Reports open with the `EVALUATOR_SELF_TEST` heading and banner |
| `run --model local --base-url http://10.0.0.5:11434/v1` | candidate | `refused: only a literal loopback model URL may be evaluated`, exit 2, before any request |
| Frontend assistant Vitest (7 files) | not rerun | No `apps/frontend` diff. Not run to avoid writing a Vitest cache through the `node_modules` junction into the primary checkout. Implementer's 87/87 is reused (frontend content identical to base) |
| `assistant-streaming` Playwright E2E | not rerun | No frontend/API change; no long-lived server started per instructions. Implementer's 1/1 reused |
| `pre_pr_check.py` | not run | Publication-stage gate; not applicable to a FAIL |

### 4.2 Behavioural parity (independent differential probe)

A scratch script drove `create_app` from the base tree and from the candidate tree in separate
processes and serialised every response and every message list sent to the model:
2 knowledge modes (none; temporary guidance + seed with a fixed store clock) × 9 model
behaviours (allowed line, allowed + disallowed line, transport failure, model disabled, free
prose, partial stream with a kept line, partial stream with an unfinished line, cut short,
knowledge-only reply) × 2 routes × 7 inputs (two questions with and without history, `hi`,
`thanks`, a 5,000-character question, an empty question, a malformed body), plus 6 auth/origin
error cases and 2 real-adapter round trips capturing the outgoing HTTP request (method, URL,
every header, body). 261 cases: 146×200, 108×422, 4×401, 2×403; 38 model answers, 108 case-data
answers; all four notices exercised; 32 cases with a `KNOWLEDGE` message.

Results: candidate (telemetry default) vs base — **byte-identical**. Candidate with
`MemorySink`, with `LogSink`, and with a sink that raises — each **byte-identical to base**.

### 4.3 Telemetry adversarial review

- Every field is built from counts, closed codes, a uuid4 hex, a SHA-256 prefix, a hashed entry
  id, retrieval floats and bools, or the operator-configured model name; validation runs in
  `__post_init__` and errors name the field only. `MetricsRecorder` catches and counts any build
  or sink failure without logging it, so exception text cannot leak.
- `emit` in the stream generator's `finally` (`main.py:517-519`) is synchronous and cannot raise
  (recorder swallows `Exception`); it does not alter control flow. `delivered` is set only after
  the final `done` event is resumed past; the disconnect test (raw ASGI `http.disconnect`)
  records `cancelled=True`. Semantics notes in L3.
- Exactly one record per answered request is also asserted implicitly by the runner for every
  harness turn (`runner.py:262-263`).

### 4.4 Harness adversarial review and F-1 reproduction

- Offline: CLM via `httpx.MockTransport`, embeddings off (`NoEmbedder`), ChromaDB telemetry off
  (pre-existing `CHROMA_SETTINGS`), measured app built from `model_construct` defaults (env and
  `.env` ignored for that app), loopback-only local model with proxy-variable refusal, runtime
  package never imports `assistant_eval` (test plus my grep).
- Snapshot equivalence: `test_a_snapshot_is_exactly_what_the_model_was_sent` compares the
  fingerprint of the messages the model received with the snapshot and checks every tagged
  knowledge line is in the `KNOWLEDGE` message; the offered set equals the guard's `_allowed`
  set (`guardrails.py:502-503`: catalog + knowledge lines). Line ids exclude tags.
- Scoring arithmetic (precision/recall/F1 micro and macro, primary, must-not, citation,
  stability, consistency, drift exclusion) reviewed line by line; no arithmetic bug found;
  edge semantics in L7. `GoldTurn` coherence rules prevent a zero-relevant non-fallback turn,
  so recall cannot divide by zero.
- **F-1 reproduction.** `Retriever` is created inside `create_app` (`main.py:250`) with its
  default clock `datetime.now(UTC)` (`knowledge/retrieval.py:165, 238`); recency decays with a
  180-day half-life and scores are rounded to 4 decimals (`retrieval.py:142-152, 269-270`).
  The harness fixes only the store clock (`runner.py:48, 84-85`). Rebuilding the snapshots with
  the retriever clock patched (scratch probes; nothing written to the repo):

  | Retriever clock | Result vs committed `snapshots.json` |
  |---|---|
  | 2026-10-26 00:00 UTC | drifted, 7 turns |
  | 01:00 UTC | drifted, 6 turns |
  | 01:45 UTC | drifted, 1 turn |
  | 02:15 and 02:30 UTC | **current** (the build window) |
  | now (≈03:05 UTC) | drifted, 5 turns, score-only (e.g. `guidance.address-mismatch` 0.964 → 0.9639) |
  | +1, +2, +7, +30, +90, +180 days | drifted, 77 turns; **3 turns (S06#0–#2) change offered lines and prompt fingerprint** (e.g. S06#1 offered 15 → 12, `resolution.synthetic-address-moved-office` drops out, confidence high → none) |

  The run-time drift flag (`runner.py:274-277`) compares only fingerprint and offered ids, so
  from day one onward S06#0–#2 are flagged and excluded from gold-based scores with no code
  change, and `check` cannot stay green. `test_snapshots_are_deterministic`
  (`tests/test_eval_harness.py:186`) builds twice within seconds and cannot detect this.

### 4.5 Token breakdown recomputation

From `snapshots.json` (64 single-question turns; C01–C05 conversations): rules 1,722; facts
mean 5,443 / median 6,073 / p95 6,329; knowledge 2,564 / 2,909 / 4,137 / max 4,368; terms,
history, question and totals (mean 9,775, median 10,339, p95 11,059, max 12,221); shares
17.6 / 55.7 / 26.2 %; profile table (56/4/4 questions; 9,928/9,584/7,827); conversation table
(9,187 → 10,745 total, history 470/1,003/1,503, max 726/1,453/2,178; largest turn 12,939 chars
= 4,313 tokens ÷3); offered lines mean 33.83 (12–51); catalog line mean 91 (max 152) — all
match. All 27 cost cells and the per-1,000 and US$10 coverage figures recompute exactly.
Labels EXACT (characters) / APPROXIMATE (tokens) / ASSUMPTION (reasoning) / prices as at
2026-10-26, not re-fetched — present.

### 4.6 Socket-guard probe

On this host (`ProactorEventLoop`), a patched `socket.socket.connect` saw a synchronous
`create_connection` but **not** an anyio/asyncio TCP connect to `127.0.0.1:1` (only the loop's
internal socketpair) — see L1.

## 5. Code and Architecture Review

| ID | Severity | Location | Finding |
|---|---|---|---|
| **F-1** | **Medium (blocking)** | `apps/assistant/assistant_eval/runner.py:48, 66-69, 84-85`; `apps/assistant/ai_assistant/main.py:250`; `apps/assistant/ai_assistant/knowledge/retrieval.py:142-152, 165, 269-270`; `apps/assistant/tests/test_eval_harness.py:186`; `.ai-pipeline/reports/AI_ASSISTANT_PHASE_A1_IMPLEMENTATION.md:88, 150-151` | Frozen snapshots depend on the wall clock through retriever recency: `check` fails on the reviewed content within hours of the build, and after one day three turns change their offered lines and are excluded from gold scoring. The determinism test cannot detect it; the handoff's "current" row is stale and deviation 8 materially understates the effect |
| L1 | Low | `apps/assistant/tests/test_eval_harness.py:45-69` | The socket guard patches `socket.socket.connect/connect_ex` only; on Windows asyncio (Proactor) connects bypass it, and `/chat/stream` (the harness route) uses the async model client. Defence-in-depth gap; no current remote path |
| L2 | Low | `apps/assistant/assistant_eval/gold.py:168-190` | The self-test gold rule picks the first two offered lines, which for every question are the same two fixed catalog lines, so E0 "perfect" never exercises knowledge-line (`K-`) selection, knowledge primary hits or citation scoring (perfect: 0 citation turns; random: 139 citation turns, rate 0.0 by construction) |
| L3 | Low | `apps/assistant/ai_assistant/main.py:509-519, 572-574` | `cancelled` is also true when an unexpected (non-`LlmUnavailableError`) exception ends the stream; `/chat` emits no record on such an exception; a stream whose generator never starts emits none. Metrics semantics only; answers unaffected |
| L4 | Low (docs) | `apps/assistant/assistant_eval/runner.py:10-11`; README "Offline evaluation" | "environment and `.env` ignored" is true for the measured app only; importing `ai_assistant.main` still composes the module-level production app from env/`.env` and opens/reconciles the default knowledge store (pre-existing import side effect; loopback-only embedder). Worth stating, and revisiting before A2 adds a remote profile |
| L5 | Low (docs) | `apps/assistant/assistant_eval/scenarios.py:32`; telemetry field list | Unlisted planner deviations: knowledge profile `guidance+seed+fix` not implemented (`none` added); 6.3 `profile` omitted; `cited_tags` → `cited_sources` count; `entries.key` → opaque `ref` (all defensible) |
| L6 | Low | `apps/assistant/assistant_eval/scoring.py:60-65, 225-231` | `score()` labels any owner-kind gold `MODEL_EVALUATION` and relies on the caller to have run `gold.verify`; the CLI does, a programmatic caller might not |
| L7 | Low | `apps/assistant/assistant_eval/scoring.py:171-176, 196-197` | When nothing is shown `f1_micro` is `None` while `f1_macro` is 0.0; consistency is 1.0 for a model that always falls back (empty vs empty Jaccard) — could flatter a weak model in a later MODEL report |

Scope and coupling: `telemetry.py` is a clean single owner; `main.py` changes are additive
bookkeeping around unchanged response construction; `assistant_eval` depends on runtime
internals (`Prepared`, `allowed_guidance`, knowledge internals), an accepted dev-only coupling
that makes snapshots drift on prompt/catalog/retrieval changes (documented). Packaging is
unaffected (`setuptools.packages.find include = ["ai_assistant*"]`). No refactor, rename or
dependency churn. Coordination risk with two teammate branches touching `main.py`/`prompts.py`
is recorded in the handoff.

## 6. Security Review

| ID | Severity | Location | Finding |
|---|---|---|---|
| — | — | — | No secret, token, key, `.env` content, PII or sponsor artefact added (`check_secrets.py` pass; added-line pattern scan clean; `OPENROUTER_API_KEY` named only in Markdown, never read) |
| L8 | Info | `apps/assistant/ai_assistant/telemetry.py:72` | `_MODEL_NAME` accepts any 1–100 character `[A-Za-z0-9._:/@+-]` string; a mis-set `AI_ASSISTANT_LLM_MODEL` containing a credential would be logged with telemetry `log`. Operator configuration only |
| L9 | Info | `.ai-pipeline/reports/AI_ASSISTANT_OPENROUTER_120B_INVESTIGATION_20261026.md` §5.2 | The investigation report becomes tracked with a facts figure (4,605) that the A1 report corrects (3,307) only in its own §5; an erratum note would avoid citing the wrong number |
| L10 | Info | `apps/assistant/assistant_eval/models.py:44-51, 216` | Proxy refusal checks environment variables only; on Windows httpx also honours registry proxy settings. This host has none (`urllib.request.getproxies()` keys: none). Harness data is synthetic |

Containment: telemetry is off by default and content-free by validation; the `on_prepared`
seam exposes facts and prompts in-process only, is never set from settings, and is documented
as harness-only. All harness data is synthetic (Garden fixtures: `GARDEN BUSINESS`,
`11111999A`; variants labelled synthetic; no case id, company name or UEN in the eval fixtures).

## 7. Required Fixes

Current blocker (F-1) — remediation in a distinct Stage 1 run:

1. Make the snapshot content a pure function of code and fixtures (remove the wall-clock input
   to retrieval in the harness, for example a fixed retriever clock equal to the store clock or
   an equivalent documented approach) without changing any runtime default. If a new
   `create_app` seam is needed, it must default to today's behaviour, and the parity evidence
   in section 4.2 must be rerun.
2. Add a regression test proving snapshots are identical when the wall clock moves (for example
   rebuild at +1 and +180 days and compare SHA-256), so 7.3.5 covers time.
3. Regenerate `tests/fixtures/eval/snapshots.json` and the `gold.json` stubs (stubs only), then
   rerun `check` (must be current), E0, the focused tests and any check the change reaches.
4. Correct the implementation report (snapshot-currency row with time and content identity;
   deviation 8) and refresh the token breakdown's snapshot SHA and any figure that changes.

Recommended (not required for PASS): L1, L2, L4, L5; L3, L6–L10 may be recorded as accepted
limitations or A2 follow-ups.

## 8. Readiness

- **A1 publication: NOT READY.** Return to bounded remediation of F-1, then a fresh independent
  re-QG of the corrected delta. Reusable without rerun unless the remediation touches them: WP1
  code and tests, telemetry privacy evidence, the base-vs-candidate failure-set comparison, the
  parity probe (rerun if `main.py` changes), lint/type/repo checks for unchanged files, and the
  token-breakdown verification for figures that do not change.
- **A2: not authorised and not started**; nothing here authorises it.
- No Live, remote-inference, OpenRouter or sponsor readiness follows from this gate. Real ACRA
  and GoldTier integration readiness are unaffected (assistant-only change).

## 9. Git Status

- Branch `feat/assistant-phase-a1-20261026`, HEAD `7effd00` (tree `5a00fd2`), base/`origin/main`
  `1d03986`; no upstream push observed by this gate.
- Before this report: no staged, modified or untracked files (ignored only:
  `apps/assistant/{.mypy_cache,.ruff_cache,data}`, `tmp/`, `apps/frontend/node_modules`); the
  git-ignored `apps/assistant/data/knowledge` timestamps are unchanged by this gate.
- This gate's only repository write is this untracked report. No implementation, test,
  fixture or document fix; no stage, commit, stash, reset, checkout, push, branch, PR, merge or
  next-phase work occurred. All probes and outputs live in the reviewer's scratch folder.
