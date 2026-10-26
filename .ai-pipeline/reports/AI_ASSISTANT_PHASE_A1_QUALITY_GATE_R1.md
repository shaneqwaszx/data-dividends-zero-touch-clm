# AI Assistant Phase A1 — Independent Re-Quality Gate after Remediation R1

| Item | Value |
|---|---|
| Date | 2026-10-26 (checks run about 03:25–03:55 UTC) |
| Role | Fresh independent re-QUALITY GATE (Stage 3). This reviewer did not author or remediate the content and did not run the first gate |
| Scope authority | Owner authorisation for A1 (WP1 + WP2) in `.ai-pipeline/001_planner/AI_ASSISTANT_PHASE_A_PLAN.md` (A-1, A-3, A-6, A-7, F-A2-1). WP3/WP4 (A2) are not authorised |
| Worktree / branch | `C:\Users\shane\Desktop\claude-worktrees\assistant-phase-a1-20261026` / `feat/assistant-phase-a1-20261026` |
| **Reviewed content** | HEAD `d9a7b4673b365098ed273a527f64d7ab2c149a49`, tree `094a95dcecd5fd37580fb247cf73d5472e548f52` |
| Commits | `d860153` (product), `7effd00` (docs; first gate FAIL reviewed this one), `d9a7b46` (remediation R1 plus the first gate report) |
| Base = `origin/main` (local ref, not re-fetched: no network) | `1d039865bf5197a76add7f733128829bb05019ac`. The merge-base is identical, so there is no integration drift against the recorded base |
| Whole A1 change `1d03986..d9a7b46` | 26 files, +6,964/−46 (`--stat` = `--ignore-cr-at-eol`) |
| R1 delta `7effd00..d9a7b46` | 15 files, +562/−82: `main.py` (clock seam), `assistant_eval/{gold,models,runner,scoring}.py`, `scripts/evaluate_answers.py`, `tests/test_eval_harness.py`, `tests/fixtures/eval/{gold,snapshots}.json`, `README.md`, `docs/ARCHITECTURE.md`, the implementation report, the token breakdown, the investigation report and the first QG report (added) |
| Change classes | `AUTH_RBAC_SECURITY` (logging/redaction), `ARCHITECTURE_REFACTOR` (injection seams, dev-only package), `CI_TOOLING` (repository script), `DOCS_ONLY` |

## 1. Executive Result

**PASS** for the exact content `d9a7b46` / tree `094a95d`.

The first gate's one blocking finding is closed. **F-1:** `create_app(retrieval_clock=)` passes
`None` through to the unchanged `Retriever(clock=)`, so the runtime default stays
`datetime.now(UTC)`. The harness pins retrieval "now" to the store clock's instant. I rebuilt
the snapshots in separate processes with the wall clock (both the retrieval and store modules)
moved from −10 years to +10 years, with varied `PYTHONHASHSEED` values and with hostile
`AI_ASSISTANT_*` environment settings. Every rebuild equals the committed fixture (sha256
`9341411d512d3beb…`), and `evaluate_answers.py check` reports current. I also ran a negative
control: the same tree with only the harness clock line removed. It drifts by 8 turns now and
by 77 turns after one day (S06#0–#2 change their offered lines), and the new regression test
`test_snapshots_do_not_change_with_the_date[1, 180]` fails there. That proves the test is a
real regression test.

**Parity:** I ran an independent differential probe over 318 cases plus 4 real-adapter
requests. Its output is byte-identical (same SHA-256) between base `1d03986` and the candidate
in 6 modes: default, explicit `None` seams, `MemorySink` (184 records), `telemetry=log` (184
lines), a raising sink (184 calls) and an explicit `retrieval_clock`. The probe is sensitive to
the retrieval clock: moving it changes 65 keys.

All ten low findings are fixed, documented or accepted as the remediation says, and I found no
regression. The full assistant suite has the same failure set as the untouched base: exactly
the 7 Windows `Errno 24` environment failures. My only new observations are non-blocking:
documentation-currency and defence-in-depth notes (section 5). None is a required fix.

## 2. First-gate findings: re-gate disposition

| ID | First-gate finding | R1 disposition | Re-gate result | Evidence |
|---|---|---|---|---|
| **F-1** | Snapshots depended on the wall clock through retrieval recency | Fixed | **CLOSED** | `main.py:240,254` (default `None` → `Retriever` default `lambda: datetime.now(UTC)`, `retrieval.py:165`); `runner.py:53-54,228,315`. 14 clock/seed rebuilds all equal the fixture; the negative control fails (section 4.2); `check` current at 03:44:45 UTC and under hostile env |
| L1 | Socket guard missed asyncio connects | Fixed | **CLOSED** | `test_eval_harness.py:52-127` wraps `BaseEventLoop.create_connection` and `socket.getaddrinfo` too. My scratch probe (7/7 pass) shows sync and async loopback still work, and that `httpx.AsyncClient` to an IPv4 literal, an IPv6 literal or a hostname, `httpx.Client` to an IP or hostname, and raw `socket.connect` are all refused with `RemoteConnectionBlocked`. anyio skips `getaddrinfo` for IP literals, so `create_connection` is the layer that catches them |
| L2 | Self-test gold never exercised knowledge lines or citations | Fixed | **CLOSED** | `gold.py:168-199`; E0 perfect has 77 citation turns, correct rate 1.0; random has 139, rate 0.1007 (no longer 0 by construction) |
| L3 | `cancelled` semantics; requests without a record | Documented | **CLOSED** (see N-5) | README "Limits" paragraph (`README.md:325-328`); the probe confirms 401/403/404/502 produce no record |
| L4 | Import of `ai_assistant.main` still builds the env-composed app | Documented | **CLOSED** | `runner.py:12-15`, README. Observed directly: one of my imports without a data-dir override re-opened the git-ignored `apps/assistant/data/knowledge` (section 9) |
| L5 | Unlisted planner deviations | Documented | **CLOSED** | Implementation report deviations 10–13 |
| L6 | `score()` trusted the caller to verify the lock | Fixed | **CLOSED** | `scoring.py:230-242`; CLI passes the lock (`evaluate_answers.py:156-199`); `test_owner_gold_is_scored_only_with_its_lock` |
| L7 | F1/consistency edge conventions | Fixed/documented | **CLOSED** | `scoring.py:175-176` (precision 0 when nothing is shown but lines were relevant); module docstring documents the both-empty Jaccard of 1.0. E0 prose: P 0.0, F1 0.0, F1 macro 0.0 |
| L8 | Permissive model-name pattern | Accepted | **ACCEPTED** (Info) | Operator configuration only; unchanged |
| L9 | Investigation report kept 4,605 uncorrected | Fixed | **CLOSED** | Correction note in its section 5.2; 3,307 recomputed (S04/S16/C02 facts = 3,307) |
| L10 | Proxy check read environment variables only | Fixed | **CLOSED** (see N-2) | `models.py:204-211` also refuses `urllib.request.getproxies()` http/https/all; test added. This host has no system proxies |

## 3. Acceptance checklist (owner A1 criteria)

| # | Criterion | Result | Direct evidence |
|---|---|---|---|
| 1 | WP1 content-free observability, with docs and tests | VERIFIED | `telemetry.py`; `main.py` seams; `config.py` `telemetry="off"`; README Observability and Limits; 50 telemetry tests pass |
| 2 | WP2 deterministic offline harness, with docs and tests | VERIFIED | 35 harness tests pass. Determinism holds over time, hash seed and environment (section 4.2); snapshots are a pure function of code and fixtures for a given library set (residual R-2) |
| 3 | Zero OpenRouter spend and zero remote-model calls | VERIFIED | No remote path in the code; the harness guard asserts zero remote attempts at module teardown; my CLI `local` runs to `10.0.0.5` and `localhost.example.com` were `refused`, exit 2; my probes use `MockTransport` only |
| 4 | No external-provider integration change | VERIFIED | `llm.py` untouched; `check_project_state.py` PASS |
| 5 | No WP3/WP4 | VERIFIED | No profile, usage, budget or ledger code; `OPENROUTER_API_KEY` appears only in 4 Markdown files |
| 6 | No prompt or retrieval optimisation | VERIFIED | `prompts.py`, `guardrails.py`, `knowledge/*`, `llm.py` unchanged; `ai_assistant` diff is limited to `config.py`, `main.py`, `telemetry.py` |
| 7 | No change to assistant business use cases | VERIFIED | Parity probe byte-identical in 6 modes (section 4.3) |
| 8 | No UI, API contract, notice-string or output-guard change | VERIFIED | No `apps/frontend` or `apps/backend` diff; statuses 200/401/403/404/422/502, bodies, all notice strings and NDJSON events identical |
| 9 | Default model request byte-for-byte unchanged | VERIFIED | Real `OpenAICompatibleChatModel` with a capturing transport: method, URL, every header and the body are identical for `/chat` and `/chat/stream`, with knowledge on and off, across all modes |
| 10 | Deterministic fallback semantics preserved | VERIFIED | Probe covers model down, disabled, prose, allowed plus disallowed, partial stream (kept and none), cut short, knowledge-line citation and small talk; 58 model and 126 case-data answers are identical |
| 11 | No unapproved change to existing acceptance tests | VERIFIED | Only `test_telemetry.py`, `test_eval_harness.py` and `fixtures/eval/*` added. JUnit: all 1,190 common tests have the same status as base |
| 12 | A-3: telemetry off by default | VERIFIED | Default `cand` mode: 0 records, 0 log lines; `sink_for("off")` → `NullSink` |
| 13 | A-3: strict allow-list; no `case_id`; no facts hash | VERIFIED | Unchanged since the first gate (R1 does not touch `telemetry.py`); telemetry tests pass |
| 14 | A-3: retrieval identifiers and categories content-free; sentinel test | VERIFIED | `RetrievedEntry` keeps an opaque `ref`; `test_no_case_user_or_model_content_reaches_a_record` passes |
| 15 | A-6: gold stubs only; no manufactured authoritative labels | VERIFIED | `gold.json`: kind `owner`, 84/84 `stub`, 0 labelled, `snapshot_sha256` = committed snapshots `9341411d…82d0`, byte-equal to `stubs(snapshots).to_json()`; no `gold.lock.json`; `lock()` refuses stubs and self-test gold |
| 16 | A-6: self-test results separated from model results | VERIFIED | All 4 E0 reports: `result_kind` `EVALUATOR_SELF_TEST`, banner first in Markdown and JSON, kind in the file name |
| 17 | A-7: no local model installed or used | VERIFIED | `NoEmbedder`; no local model contacted by any of my runs |
| 18 | Known Windows resource failures preserved | VERIFIED | Base and candidate both have exactly 7 `Errno 24` failures in `test_streaming_resources.py`; the same file alone gives 80 passed |
| 19 | Token breakdown: exact chars versus approximate tokens; economical and conservative costs | VERIFIED | Every single-question and conversation figure recomputed and matching (section 4.5); cost inputs unchanged since the first gate's verification |
| 20 | `OPENROUTER_API_KEY` loader mismatch recorded as an A2 follow-up; secret untouched | VERIFIED | Planner F-A2-1, implementation report §7, breakdown §5; no code reference; no value anywhere |
| 21 | Optimisation opportunities identified, not implemented | VERIFIED | Breakdown §4 T1–T8; no code |
| 22 | Implementer evidence accurate | VERIFIED with doc notes | All R1 test counts, E0 numbers, lint/type, integration, repo checks and `check` currency reproduced. Some pre-R1 description lines are stale (N-1) |

## 4. Evidence executed by this gate

Environment: Windows 11, Python 3.12.10 from the primary checkout's `.venv`; `PYTHONPATH`
pinned to the tree under test; `PYTHONDONTWRITEBYTECODE=1`; pytest `-p no:cacheprovider`;
ruff `--no-cache`; mypy cache, outputs and probes in my scratch folder;
`AI_ASSISTANT_KNOWLEDGE_DATA_DIR` set to scratch for every run except one import (section 9).

### 4.1 Commands and results

| Check | Content | Result |
|---|---|---|
| Full assistant suite `pytest -o faulthandler_timeout=300 --junitxml` | candidate `d9a7b46` | 1,275 collected: **1,268 passed, 7 failed**, 0 skipped, 164 s |
| Same, on base | `git archive 1d03986` of `apps/assistant` plus `apps/frontend/src/pages` in scratch | 1,190 collected: **1,183 passed, 7 failed**, 152 s |
| JUnit comparison | base vs candidate | Identical failure set (all `OSError: [Errno 24] Too many open files`: `test_loopback_total_deadline[no-newline, heartbeat, read-stall, headers-stall, chunk-header-trickle]`, `test_real_chunked_http_enforces_budgets[oversized, many-frames]`); 0 status differences across the 1,190 common tests; 85 new tests only from the two new files; none removed |
| `pytest tests/test_streaming_resources.py` alone | candidate | **80 passed** |
| `pytest tests/test_telemetry.py tests/test_eval_harness.py` | candidate | **85 passed** (50 + 35) |
| `ruff check` / `ruff format --check` (`ai_assistant assistant_eval tests scripts`) | candidate | All checks passed / 76 files already formatted |
| `mypy ai_assistant assistant_eval`; `mypy scripts/evaluate_answers.py` | candidate | No issues in 36 / 1 source files |
| Backend `pytest tests/test_ai_assistant_main_integration.py` | candidate (test inserts the worktree `apps/assistant`; confirmed `create_app` has `retrieval_clock`) | **2 passed** |
| `scripts/check_secrets.py`; `check_architecture.py`; `check_project_state.py` | worktree root | pass / PASS / PASS |
| `git diff --check 1d03986..d9a7b46`; trailing-whitespace and final-newline scan of all 26 changed files | committed content | clean |
| `docs/ARCHITECTURE.md` EOL | blobs | `1d03986` 1,007 CRLF + 98 LF → `7effd00` 1,023 + 98 → `d9a7b46` 1,024 + 98; R1's 2 lines are CRLF like their neighbours; `--stat` = `--ignore-cr-at-eol` |
| `scripts/evaluate_answers.py check` | candidate, 03:44:45 UTC | **`snapshots are current (84 turns, sha256 9341411d512d3beb)`**, exit 0 |
| Same, with `AI_ASSISTANT_RETRIEVAL_WEIGHT_RECENCY=0.9`, `…_KEYWORD=0.9`, `…_MAX_HISTORY_MESSAGES=2`, `…_RETRIEVAL_MAX_GUIDANCE=1`, `…_TELEMETRY=log`, `…_KNOWLEDGE_ENABLED=false`, `…_MAX_QUESTION_CHARS=20`, `PYTHONHASHSEED=987` | candidate | current, exit 0 (the measured app ignores the environment) |
| `run --model self-test-{perfect,prose,injection}`; `self-test-random --reps 2` (out: scratch) | candidate | Matches the implementation report E0 table (section 4.4) |
| `run --model local --base-url http://10.0.0.5:11434/v1` and `http://localhost.example.com:11434/v1` | candidate | `refused: only a literal loopback model URL may be evaluated`, exit 2 |
| Frontend assistant Vitest; `assistant-streaming` E2E | not rerun | No frontend or API diff in A1. The E2E uses its own Node synthetic server (`e2e/assistant-streaming.e2e.ts:1,48`). The implementer's 87/87 and 1/1 are reused as valid for unchanged content |
| `pre_pr_check.py` | not run | Publication-stage gate (Stage 4) |
| Hosted CI | not executed | Assistant tests are not in CI; hosted CI has been billing-blocked (not observed by this gate) |

### 4.2 F-1 closure: date, seed and environment independence

The probe `probe_dates.py` (scratch) runs in a separate process per row. It patches the
`datetime` used by `ai_assistant.knowledge.retrieval` (the default retrieval clock) and by
`ai_assistant.knowledge.store` (the default store clock), then rebuilds the snapshots with
the real harness and compares them with the committed fixture.

| Tree | Clock | Result |
|---|---|---|
| candidate | now −3650 d, −30 d, now, +12 h, +1 d, +7 d, +180 d, +3650 d (random `PYTHONHASHSEED`) | all **equal** (`9341411d512d3beb`), 0 turns changed |
| candidate | absolute 2020-01-01 (before every approval date), 2026-10-26T00:00Z, 2040-06-30 | all **equal** |
| candidate | +2 d with `PYTHONHASHSEED` 0, 1, 4242 | all **equal** |
| **negative control** (candidate with only `runner.py:228` removed) | now | drifted, 8 turns |
| negative control | +1 d / +180 d | drifted, 77 turns; **S06#0–#2 change offered lines and prompt** |
| negative control | `pytest test_snapshots_do_not_change_with_the_date test_snapshots_are_deterministic` | `[1]` and `[180]` **FAIL** (sha mismatch); same-minute determinism still passes, as the first gate observed |

Other sources of non-determinism I checked:

- The only wall-clock reads in the runtime package are `store.py:156` (pinned by the harness
  store clock) and `retrieval.py:165` (now pinned). `uuid4` affects telemetry `request_id`
  only, never snapshots. `report.py` and `gold.lock` timestamps are outside snapshots.
- `ingest_guidance` reads `sorted(glob)` files as UTF-8. Hit ties sort by `entry_id`.
  Snapshot JSON is key-sorted. `prompt_version` hashes source through `inspect.getsource`,
  which uses universal newlines, so CRLF and LF checkouts agree.
- The committed `snapshots.json` equals `SnapshotSet.to_json()` byte for byte (after EOL
  normalisation), so it is tool-generated.

### 4.3 Behavioural parity: base vs candidate (independent probe)

The probe `probe_parity.py` (scratch) runs one separate process per mode. It drives
`create_app` from base `1d03986` (git archive) and from the candidate worktree. Retrieval "now"
is pinned identically in every mode by patching the retrieval module's `datetime`, except in
the explicit-clock mode, which passes the same instant through `retrieval_clock`. The store
clock is fixed.

The inputs are 2 knowledge modes (none; repository guidance plus seed) × 9 model behaviours
(allowed line; allowed plus disallowed; transport failure; disabled; free prose; partial
stream with a kept line; partial stream with an unfinished line; cut short; selecting a
tagged knowledge line) × (`/brief` + 2 routes × 8 inputs: question, question with history,
knowledge question, `hi`, `thanks`, an over-long question, empty, malformed). On top of that
come 8 error cases (no cookie, foreign origin, backend 500, unknown case, on both routes) and
4 real-adapter round trips that capture method, URL, every header and the body. In total:
318 responses (202×200, 108×422, 2×401, 2×403, 2×404, 2×502), 58 model answers, 126
case-data answers, every notice string, 33 answers with a cited source and 48 model calls
with a `KNOWLEDGE` message.

| Mode | Output SHA-256 | Telemetry activity |
|---|---|---|
| base | `30573433f5da…99ef68` | — |
| candidate default | identical | 0 records |
| candidate, `metrics=None, on_prepared=None, retrieval_clock=None` | identical | 0 |
| candidate, `MemorySink` | identical | 184 records (= answered requests, 1 each) |
| candidate, `telemetry="log"` | identical | 184 JSON lines |
| candidate, raising sink | identical | 184 sink calls, all swallowed |
| candidate, `retrieval_clock=lambda: FIXED` (module unpatched) | identical | 0 |
| **sensitivity check:** base with "now" moved to 2031-06-01 | 65 keys differ | — |

The sensitivity row shows that the probe would detect a clock that was not passed through.
So the default seam behaves exactly like the previous code, and an explicit seam reproduces
it.

### 4.4 E0 self-tests (EVALUATOR_SELF_TEST; not model results)

| Selector | Validity | Fallback | Unsafe | P / R / F1 (micro) | Citations scored / correct | Other |
|---|---|---|---|---|---|---|
| perfect | 1.0 | 0.0 | 0 | 1.0 / 1.0 / 1.0 | 77 / 1.0 | primary 1.0; must-not 0 |
| random (seed 7, 2 reps) | 1.0 | 0.0 | 0 | 0.0635 / 0.0952 / 0.0762 | 139 / 0.1007 | stability 0.0583; must-not 19 |
| prose | 0.0 | 1.0 (`policy_no_allowed_line` ×84) | 0 | 0.0 / 0.0 / 0.0 (macro 0.0) | 0 / — | consistency 1.0 (documented both-empty convention) |
| injection | 0.2 | 0.0 | 0 | 1.0 / 0.5 / 0.6667 | 0 / — | injected lines never shown |

All reports record `retrieval_clock` `2026-10-26T00:00:00+00:00`, have 0 drifted turns, and
open with the `EVALUATOR_SELF_TEST` heading and banner. The figures match the implementation
report's E0 table.

### 4.5 Token breakdown recomputation

Single questions (64), from the committed snapshots:

| Part | Mean | Median | p95 | Max | Share |
|---|---|---|---|---|---|
| rules | 1,722 | | | | 17.6 % |
| facts | 5,443 | 6,073 | 6,329 | 6,329 | 55.7 % |
| knowledge | 2,564 | 2,909 | 4,137 | 4,368 | 26.2 % |
| terms | 14 | | 138 | 290 | |
| history | 5 | | 84 | | |
| question | 27 | 25 | 49 | 53 | |
| total | 9,775 | 10,339 | 11,059 | 12,221 | |

Other single-question figures: profiles 56/4/4 questions (14/1/1 scenarios); offered lines
33.83 on average (12–51); catalog lines 91 characters on average (max 152); 73 distinct lines.

Conversations, from my own harness runs:

- Two-line self-test answers: totals 9,187 / 9,540 / 9,739 / 9,864; history mean / max
  0 / 0, 190 / 229, 401 / 448, 623 / 689.
- Fallback answers: totals 9,187 / 9,820 / 10,341 / 10,745; history 0 / 0, 470 / 726,
  1,003 / 1,453, 1,503 / 2,178; largest turn 12,939 characters (4,313 tokens at ÷3).

**All match the R1 breakdown.** R1 changed only retrieval scores (8 score values) and the
manifest key in `snapshots.json`; part sizes and offered lines are unchanged, so the first
gate's cost-cell verification still holds.

## 5. Code and Architecture Review

R1 is tightly scoped. In `main.py` it adds one keyword parameter, one pass-through and a
docstring. The harness uses the existing `Retriever(clock=)` hook. No runtime default,
setting, route or response construction changed. `retrieval_clock` and `on_prepared` are set
only by `assistant_eval/runner.py:227-228`, never from settings. Production composition
(`main.py:630`) passes neither. `ai_assistant` still never imports `assistant_eval`.

New observations (none blocking; none is a required fix):

| ID | Severity | Location | Observation | Suggested handling |
|---|---|---|---|---|
| N-1 | Low (docs, handoff only) | `.ai-pipeline/reports/AI_ASSISTANT_PHASE_A1_IMPLEMENTATION.md:22, 42, 43, 50, 72` | Pre-R1 description rows are stale: `create_app(metrics=, on_prepared=)` and "two `create_app` injection seams" (now three), runner "fixed store clock" (both clocks now), `local_model` "refused when a proxy variable is set" (system proxies too), "30 tests" (now 35). Sections 3, 4 and 10 of the same report state the current content correctly, and the durable docs (README, ARCHITECTURE, docstrings) are accurate | Describe three seams and 35 tests in the PR description; correct the rows with any later edit |
| N-2 | Info | `apps/assistant/assistant_eval/models.py:201-211` | Both proxy refusals inspect the `environ` argument when one is passed, and the system-proxy check is skipped entirely. The returned adapter's `httpx` clients still honour real `os.environ` and system proxies (`trust_env` default). Only tests pass `environ` (and they send nothing); the CLI never does | A2/WP3: evaluate with `trust_env=False`, or always check the real process and system proxy settings |
| N-3 | Info | `apps/assistant/tests/test_eval_harness.py:110-127` | The self-check clears the module-wide `attempts` list. That would also erase attempts recorded by earlier tests if test order changed; today it runs first. Its blocking-connect assertion is satisfied at the `getaddrinfo` layer, because `socket.create_connection` resolves first, so the `socket.socket.connect` wrapper is not self-checked directly (my probe showed it works). On a guard regression, the `example.com` lookup would leave the host | Truncate only its own entries; consider a raw `connect` assertion |
| N-4 | Info | `apps/assistant/tests/test_eval_harness.py:248-266`; `runner.py:91` | The date regression test moves only the retrieval module's clock and reuses the module workspace. A regression that dropped the store clock would be caught by `check` (fresh workspace), not by the unit tests | Optional: also patch the store module's clock with a fresh `Workspace` |
| N-5 | Info | `apps/assistant/README.md:325-328` | The Limits paragraph does not mention the first gate's L3 case of a stream whose body is never iterated: a client gone before the first event leaves no record | Optional wording |

Accepted coupling (unchanged from the first gate): `assistant_eval` depends on runtime
internals, so prompt, catalog or retrieval edits make the snapshots drift. This is documented
and detected by `check` and by per-run drift flags. Packaging is unchanged. There is no
refactor, rename or dependency churn.

## 6. Security Review

- **Secrets and data:** no secret, token, `.env` content, PII or sponsor artefact was added.
  `check_secrets.py` passes and my added-line pattern scan is clean. `OPENROUTER_API_KEY` is
  named only in the planner, implementation report, token breakdown and first QG report
  (Markdown), never read. I did not open any `.env` file; none exists in the worktree root or
  in `apps/assistant`.
- **Telemetry:** R1 does not change `telemetry.py`. Off by default and content-free by
  validation are re-confirmed by the parity probe (0 records by default) and by the passing
  sentinel test.
- **Network containment:** the harness guard is now effective on Windows asyncio (L1 closed).
  `local_model` refuses non-loopback URLs, proxy variables and system proxies on the CLI path.
  N-2 is an Info-level gap for programmatic callers only. All harness data is synthetic.
- **Seams:** `on_prepared` still exposes case facts in-process to the harness only.
  `retrieval_clock` carries no data. Neither is reachable from settings or the environment.

## 7. Required Fixes

**None.** N-1 to N-5 are optional or later (A2/WP3) improvements. Changing any reviewed file,
including the reports, changes the reviewed content and needs a fresh independent recheck
before publication.

## 8. Readiness

- **A1 publication readiness:** content `d9a7b46` / tree `094a95d` has an independent
  **PASS**. The remaining Stage 4 prerequisites are not part of this gate:
  - explicit owner authorisation;
  - a fetch and drift check against the latest `origin/main` (not fetched here: no network);
  - unchanged reviewed content;
  - scoped staging;
  - a clean-tree `python scripts/pre_pr_check.py`.

  This report is a new untracked file; it is not reviewed product content.
- **A2:** not authorised and not started. Nothing here authorises WP3/WP4, OpenRouter access,
  a remote profile or any spend.
- No Live, remote-inference, OpenRouter or sponsor readiness follows from this gate. Real ACRA
  and GoldTier integration readiness are unaffected (assistant-only change).

## 9. Git Status

- Branch `feat/assistant-phase-a1-20261026`, HEAD `d9a7b46` (tree `094a95d`), base and local
  `origin/main` `1d03986`.
- Before this report, `git status` showed no staged, modified or untracked files. Ignored
  only: `apps/assistant/{.mypy_cache,.ruff_cache,data}`, `apps/frontend/node_modules`, `tmp/`.
- **Disclosure:** one verification command, a bare `python -c` import of `ai_assistant.main`
  run from `apps/backend` to confirm which tree the backend test imports, ran without the
  scratch `AI_ASSISTANT_KNOWLEDGE_DATA_DIR` override. Through the pre-existing module-level
  app (L4), it re-opened and reconciled the **git-ignored** `apps/assistant/data/knowledge`
  store (modification time 03:50 UTC). No tracked file was affected. Every other run used
  the scratch data directory.
- This gate's only repository write is this untracked report. There was no implementation,
  test, fixture or document fix, and no stage, commit, stash, reset, checkout, push, branch,
  PR, merge or next-phase work. All probes, archives, JUnit files and E0 reports are in the
  reviewer's scratch folder. No network beyond loopback was used, and no model or API was
  called.
