# AI Assistant Phase A2 — Remediation R2 — Independent re-Quality Gate

| Item | Value |
|---|---|
| Date | 2026-10-26 |
| Role | Fresh independent Stage 3 re-Quality Gate (`fyp-quality-gate`). This reviewer did not implement A2, R1 or R2 and did not run either earlier gate |
| Reviewed commit | `e0d45d4bfa4ec0853f8f9a498a6ce659b1396144` (local branch `feat/assistant-phase-a2-20261026-int`, no upstream) |
| Reviewed tree | `859ec51a51927f98817908d0c034e987a850e8d9` = expected |
| Parents | `ee8a658` (R1, re-QG PASS) → `5245bbe` (A2, QG PASS) → base `7d6a31a` |
| Review snapshot | Reviewer-owned `git clone --shared --no-checkout` of the implementing worktree, detached at `e0d45d4` (`core.longpaths` set in the clone only), under this session's scratchpad `reqg2\snap`. `git archive ee8a658 apps/assistant` (`reqg2\mid`) for differential probes. A copy of the base `7d6a31a` `apps/assistant` archive (`reqg2\base`). The implementing worktree, its branch and the primary checkout were only read |
| Remote activity / spend | **Zero** OpenRouter or other non-loopback requests. **US$0.00**. `OPENROUTER_API_KEY` never read (names-only check: not set; every Python run used `env -u OPENROUTER_API_KEY`). No `.env` opened |

## 1. Verdict

**PASS** for `e0d45d4` (tree `859ec51a`).

- **N-1: CLOSED.** The non-stream path now keeps the status class when the bounded error-body
  read times out or fails, matching the stream path. No other error path changed, and the
  deadline and byte bounds still hold.
- **N-2: CLOSED** for the reported shapes and every punctuation, nested-bracket and quoting
  variant that puts a literal directly after the placeholder. One residual shape remains: a
  backtick, quote or `#` terminator *followed by* a literal. It is recorded as **R2-1 (Low)**.
  R2 did not introduce it: it is the R1 shape that R2's lookahead does not reach, and the
  quote and `#` forms were already accepted on `5245bbe`.
- F-1 to F-6 are not regressed. Locks L1–L4, S1–S3, INV-1 to INV-9, default-profile parity and
  governance all still hold.
- The full assistant suite has the same 12 Windows `Errno 24` failures as base, plus the guard
  self-test, which hits the same limit. All 13 pass when run alone. There are no regressions.

The only new findings are Low and informational. None can cause a remote request or spending,
and none affects the default profile. They do not block the dormant merge, and they are
recommended before Phase B (owner's choice).

## 2. Identity checks (passed before review)

| Check | Result |
|---|---|
| Worktree HEAD / tree | `e0d45d4bfa4e…6144` / `859ec51a5192…e8d9` ✓, checked at start and end |
| Branch | `feat/assistant-phase-a2-20261026-int` ✓; parents `ee8a658` → `5245bbe` → `7d6a31a` ✓ |
| Worktree status | 0 tracked or untracked changes at start and end |
| `ee8a658..e0d45d4` | exactly the 6 expected files, +97/−3: `openrouter.py` (+8/−1), `test_openrouter_adapter.py` (+31), `test_budget_guard.py` (+14), `scripts/check_secrets.py` (+5/−1), `tests/test_check_secrets.py` (+27), implementation report (+12/−1). `--numstat` equals `--numstat --ignore-cr-at-eol` (no EOL churn) |
| Unchanged by R2 | `budget.py`, `model_factory.py`, `model_profiles.py`, `config.py`, `main.py`, `llm.py`, `telemetry.py`, `scripts/budget_ledger.py`, `conftest.py`, `remote_fixtures.py`, all of `docs/`, backend and frontend |
| Snapshot | HEAD/tree equal to the candidate; `git status` clean; every probe asserts `ai_assistant.__file__` is under `reqg2\snap` |

## 3. N-1 — CLOSED

**Code** (`apps/assistant/ai_assistant/openrouter.py:321-333`). When `status != 200`,
`_bounded_body(response, MAX_ERROR_BODY_BYTES, deadline)` is now wrapped in
`try/except (ModelCallError, httpx.HTTPError, httpx.StreamError)`, and on failure
`error_body = b""`. `ModelCallError(_status_class(status, …))` is then raised as before. This
mirrors `_error_body` on the stream path (`:367-382`): the same three exception families
(`ModelCallError("timeout")` is the sync form of the async `TimeoutError`), a bounded body, and
a status-only class when the read fails.

**Scope of the change.** The `try` covers only the error-body read. The 200 path (encoding
check, `_bounded_body(…, MAX_STREAM_BYTES, …)`), the outer `except httpx.TimeoutException` /
`httpx.HTTPError`, the post-read size and deadline checks, and the JSON handling are
byte-for-byte unchanged. `response.close()` still runs in `finally`.

**Reviewer probes** (`reqg2\probes\test_n1_probe.py`, MockTransport only, own non-loopback
socket guard): **127/127 passed** on `e0d45d4`.

| Probe | Result |
|---|---|
| `complete()`: 12 statuses (400, 401, 402, 403, 404, 408, 413, 429, 500, 502, 503, 504) × 6 bodies (slow 0.5 s > 0.3 s deadline, infinite 8-byte drip every 50 ms, read error, read timeout, partial then read error, `StreamClosed`) | 72/72: class = `_status_class(status, b"")`, exactly one request, elapsed < 1.2 s (the deadline is 0.3 s, plus at most one in-flight chunk) |
| `complete()` vs `stream()`, 5 statuses × 6 bodies | 30/30 same `error_class` on both paths |
| Error-body byte bound: 10 MiB `500` offered | `upstream`; pulled ≤ 16 KiB + one 4 KiB chunk |
| Fast `402` with `limit_source: openrouter_key_limit` | `payment_key_limit` (unchanged) |
| 200 path: slow / drip / read timeout → `timeout`; read error / partial then error → `transport`; 4 MiB → `protocol` after ≤ 1 MiB + one chunk; `gzip` → `protocol`; happy path → answer, `Accept-Encoding: identity` | all unchanged |
| Through the guard (`build_chat_model` + ledger), `/chat`'s `complete()`, 7 statuses × slow/broken | 14/14: breaker open exactly when the class is in `TRIP_ERROR_CLASSES` (401/402/403/400/404 open, 429/500 do not), `open_calls == 0` (settled once) |
| Blocked non-loopback attempts | 0 |

**Sensitivity.** The same probe file run against R1 (`ee8a658`, `reqg2\mid`) gives
**114 failed / 13 passed**: 69/72 status-class cases, 30/30 path-agreement cases and 14/14
breaker cases fail there. The 3 status cases that pass on R1 are the ones where the status
class is `timeout` anyway, and the 13th failure is the probe's own snapshot-identity check. So
the probe detects the R1 defect, and R2 removes it.

**New R2 tests.** `test_a_slow_or_broken_error_body_keeps_the_status_class` (8 cases) and
`test_a_refusal_with_a_slow_error_body_opens_the_breaker_on_chat` pass. The guard test asserts
`breaker_code == "provider_error"`.

Informational I-1 (no action needed). Unlike `_error_body`, the sync path throws away a
*partial* error body when the read fails. So for a `402` whose key-limit code arrived before a
stall, `/chat` gives `payment` while `/chat/stream` could give `payment_key_limit`. Both are in
`TRIP_ERROR_CLASSES` and both trip as `provider_error`, so breaker behaviour is identical. The
two classes are not distinguished anywhere else (`budget.py:70`, `llm.py:103`).

## 4. N-2 — CLOSED (residual R2-1, Low)

**Code** (`scripts/check_secrets.py:41-45`). The placeholder alternative is now
`<[^<>\n]{1,64}>(?=[.,;:)\]}*_]*(?:$|[\s"'`#]))`. If the lookahead fails, the alternation
falls back to `[^"'\s#]*`, which captures `<x>literal` whole, and `is_placeholder` rejects it
(`ANGLE_PLACEHOLDER.fullmatch` fails). `scan_file` and `main()` are unchanged. `main()` prints
only `path`, `line` and `rule` (`:206-212`), and every probe asserted that the literal is absent
from `repr(findings)`.

**Differential probe** (`reqg2\probes\n2_probe.py`, runs the scanners from `5245bbe`,
`ee8a658` and `e0d45d4` on the same lines; literals built at run time). **0 failures** over the
asserted cases:

| Shape | `5245bbe` | `ee8a658` | `e0d45d4` |
|---|---|---|---|
| Whole placeholders: `K=<key>`, `Set K=<your key> in…`, `"<your key>"`, `'<your key>'`, `` `K=<key>` ``, Markdown table, `.`, `;`, `(…)`, `**…**`, `<key> # c`, YAML, subscript, `K=`, CRLF | 3 FP | pass | **pass** |
| Glued literal: `<x>L`, `"<x>L"`, `'<x>L'`, YAML `<a>L`, subscript `"<x>L"` | flag (no subscript rule) | **miss** | **flag** |
| Punctuation then literal: `<x>.L`, `<x>_L`, `<x>)L`, `<x>**L` | flag | miss | **flag** |
| Nested: `<<x>L`, `<x>>L`, `<a<b>L>` | flag | 2 of 3 | **flag** |
| Plain literals, `L<x>`, `"L"` | flag | flag | **flag** |
| No new false negative versus R1 | — | — | **0** (every R1 flag is still flagged) |

**Repository.** All 2,343 tracked files of the snapshot, scanned with each of the three
scanners: **0 findings each**. `check_secrets.py` exits 0, and `tests/test_check_secrets.py`
passes 22/22 (20 earlier tests + 2 from R2).

Judgement cases, recorded and not asserted:

- **R2-1 (Low, see §5).** A terminator followed by a literal:
  `` K=<x>`L ``, `K="<x>"L`, `K=<x>"L"` and `K=<x>#L` are not flagged on `e0d45d4`. The backtick
  form *was* flagged on `5245bbe`. The quote and `#` forms were accepted on all three versions.
- **I-2 (fail-safe).** `Set K=<key>!` and `Is K=<key>?` are flagged again, as on `5245bbe` (R1
  accepted them). `K=<a><b>` and a 65-character placeholder are flagged. All of these are false
  positives that fail safe, and none occurs in the repository.
- **I-3 (unchanged since `5245bbe`).** `K="<x> L"` (placeholder, space, literal inside one quoted
  value) is accepted by all three versions, because the space ends the value class.

## 5. New findings

No critical, high or medium findings.

| ID | Severity | Location | Failure scenario | Suggested fix |
|---|---|---|---|---|
| R2-1 | Low | `scripts/check_secrets.py:44` (`CREDENTIAL_VALUE` lookahead) | The lookahead checks only the **first** character after the trailing punctuation. When that character is a backtick, quote or `#`, whatever follows it is never inspected. So `` OPENROUTER_API_KEY=<x>`LITERAL ``, `OPENROUTER_API_KEY="<x>"LITERAL` (shell concatenation gives `<x>LITERAL`), `OPENROUTER_API_KEY=<x>"LITERAL"` and `OPENROUTER_API_KEY=<x>#LITERAL` (python-dotenv keeps an unspaced `#` in the value) all pass. Impact is small: the forms are contrived, a real `sk-or-…` key on such a line is still caught by the separate `openrouter-key` rule, no tracked file is affected, and the scanner still prints no value | Make the terminator itself end the value. For example, accept a quote or backtick only when it is followed by Markdown punctuation and then end of line or whitespace: `(?=[.,;:)\]}*_]*(?:$\|\s\|#\|["'`][.,;:)\]}*_\|]*(?:$\|\s)))`, with `#` accepted only after whitespace. Add tests for the four shapes above, plus the table and quoted forms. Before Phase B, or at the owner's discretion |

Informational I-1 to I-3 are in §3 and §4. Two further points, neither needing action:

- **I-4.** Handoff §11 records the changes and test names, but not the R2 verification counts.
  The coordinator relayed those counts, and this gate reproduced them (§6).
- **I-5.** Root `ruff check .` (the CI command) reports 9 issues, all in tracked `.ai-pipeline`
  evidence scripts (`pr81-tcp-capture*/Run-FreshFixture.py`,
  `SDQ01_ROUND3_EVIDENCE/.../run_sdq01_r3_validation.py`). The A2 range does not touch them, so
  they are present on base `7d6a31a` as well. `ruff format --check` with root defaults would
  reformat the two root scanner files, but there is no root ruff configuration, the files were
  not 88-column formatted before A2 either, and CI does not run a root format check. Neither is
  an R2 finding.

## 6. Evidence

All evidence was produced by this reviewer on the frozen snapshot. Interpreter: the primary
checkout's `.venv` (Python 3.12, pytest 8.4.2, httpx 0.28.1, ruff 0.16.2, mypy 1.20.2), used
read-only with `PYTHONPATH` pinned to the snapshot. Pytest used `-p no:cacheprovider` and
`PYTHONDONTWRITEBYTECODE=1`.

| Check | Status | Result |
|---|---|---|
| Focused: `test_openrouter_adapter.py` + `test_budget_guard.py` (JUnit) | Executed | **122/122 passed** (103 + 19) |
| Focused: `tests/test_check_secrets.py` (repo root) | Executed | **22/22 passed** |
| Full assistant suite, candidate (`timeout 1800`, `faulthandler_timeout=300`, JUnit) | Executed | 1,840 collected: **1,827 passed, 13 failed, 0 errors, 0 skipped** (359 s). Matches the implementer's numbers |
| Failure classification (JUnit, test by test) | Executed | All 13 are `OSError: [Errno 24] Too many open files`: `test_required_p2::test_real_http_sse_framing` ×5, `test_streaming_resources::test_loopback_total_deadline` ×5, `::test_real_chunked_http_enforces_budgets[oversized, many-frames]`, plus `test_model_factory::test_the_suite_guard_blocks_remote_connections` |
| Isolated rerun of those two files plus the guard self-test | Executed | **148/148 passed** |
| Full assistant suite, base `7d6a31a` (same harness) | Executed | 1,574 collected: 1,561 passed, 13 failed (266 s). **12 failures are exactly the candidate's 12 `Errno 24` tests.** The 13th, `test_required_p2::test_r1_stage_inventory_matches_accepted_case_ui`, was an artefact of the reviewer's copy, which first held only `apps/assistant` (`FileNotFoundError` on `apps/frontend/src/pages/CaseDetail.tsx`). With `git archive 7d6a31a apps/frontend/src` added it passes (1/1), giving the same 1,562/12 as the prior gate. Candidate-only failure: the guard self-test (A2's new test, Errno 24, passes alone). **New regressions: 0** |
| A2 test files within the full run | Executed | `budget_cli` 17, `budget_guard` 19, `budget_ledger` 60 (INV-1–INV-9, including the randomised and two-process tests), `default_request_golden` 6, `model_factory` 61 (1 failure, Errno 24, passes alone), `openrouter_adapter` 103, `telemetry` 50 |
| Reviewer N-1 probe | Executed | 127/127 on `e0d45d4`; 114 failed on `ee8a658` (sensitivity) |
| Reviewer N-2 differential probe | Executed | 0 failures; table in §4 |
| Repository scan with the 3 scanner versions | Executed | 0 findings each over 2,343 files |
| Reviewer lock probe (`test_locks_probe.py`) | Executed | **8/8**: shipped remote profile `endpoints == ()`; default settings → `OpenAICompatibleChatModel`; no transport → `PROFILE_DORMANT`; `HTTPTransport` / `MockTransport` subclass → `TRANSPORT_NOT_ALLOWED`; shipped registry → refused (`ENDPOINT_NOT_APPROVED`/`DECISION_INTERLOCK`), with an environment that fails on any read, so the credential is never touched; missing ledger → `LEDGER_UNAVAILABLE`, with no parent directory created; test registry → `BudgetedChatModel` |
| Default-profile parity (the prior re-QG reviewer's independent loopback probe, copied to `reqg2\probes`) | Executed | Candidate run 1 = run 2: 282 responses, 253 model requests, 0 blocked, SHA-256 `95bd00d6a9d4f933ccbdef259b5d028e8f706063005d871db813d81c0146ce29`. Base `7d6a31a` gives the same hash, and the transcript files are byte-identical (`cmp`). This also equals the prior re-QG's base and `ee8a658` hash. Log capture recorded 0 lines on both trees, as before |
| Implementer's parity probe (`def72e8b…392bc`) | Not executed | Optional. An independent probe was used instead |
| `ruff check` (`ai_assistant assistant_eval scripts tests`, assistant config) | Executed | All checks passed |
| `ruff format --check` (same paths) | Executed | 92 files already formatted |
| `ruff check` on `scripts/check_secrets.py`, `tests/test_check_secrets.py` | Executed | All checks passed |
| Root `ruff check .` (CI command) | Executed | 9 issues in base-tracked `.ai-pipeline` evidence scripts; 0 in A2 files (I-5) |
| `mypy --strict` (`ai_assistant`, `assistant_eval`, `scripts/budget_ledger.py`, `scripts/evaluate_answers.py`) | Executed | Success: no issues in 43 source files |
| `check_architecture`, `check_external_provider_readiness`, `check_policy_authority`, `check_project_state`, `check_secrets`, `check_tooling_config` | Executed | all exit 0 (PASS) |
| `check_mongodb.py` | Not executed | Not applicable: no Mongo surface, and connecting to `clm_poc` is forbidden |
| `git diff --check` (`ee8a658..HEAD` and `7d6a31a..HEAD`) | Executed | clean |
| Markdown whitespace (all 7 Markdown files changed since base: trailing whitespace and tabs) | Executed | 0 / 0 |
| Tracked-secret hygiene | Executed | No `sk-or-` pattern in `7d6a31a..HEAD`; no tracked `.env`, key, certificate or SQLite ledger; `.env.example` adds only a do-not-add-the-key comment and a non-secret setting; the test key is the `test_`-prefixed sentinel |
| Backend pytest, frontend Vitest/build, assistant-streaming Playwright | Reused (by reference) | Not rerun. R2 changes no backend, frontend or e2e file, so the earlier gates' evidence on `5245bbe`/`ee8a658` (backend 3,173 passed / 177 skipped; frontend assistant Vitest 108/108; direct Playwright 1/1) is unaffected. Disclosed as reuse |
| `run_e2e.py` harness / POC lifecycle | **NOT EXECUTED** | Docker (disposable Mongo) and Tesseract are not available. Not marked passed |
| `pre_pr_check.py` | **NOT EXECUTED** | Needs separate owner authorisation |
| Hosted CI | Not executed | Nothing pushed |

## 7. Re-check of the whole candidate

- **F-1 to F-6: not regressed.** R2 does not touch `budget.py` (F-1 prompt pre-check, F-2 lag
  bounds), `model_factory.py` (F-4 bounds), the README or docstrings (F-6), or the 200 path of
  `complete()` (F-3 byte, deadline and encoding bounds, re-probed in §3). For F-5, every
  subscript, single-quote and placeholder case passes again in the N-2 matrix, and the
  repository scan is unchanged. The R1 tests in the full run all pass.
- **Locks L1–L4**: re-probed (§6). The code is unchanged since R1.
- **S1 (exact endpoint identity)**: `model_profiles.py` is unchanged, and the shipped registry
  has no endpoint. The adapter request-policy test passes. **S2 (MockTransport only, suite
  guard)**: the transport type check is unchanged (lock probe). The suite's own socket guard
  ran, and its self-test passes alone. The reviewer's probes recorded 0 blocked attempts.
  **S3 (opaque alias, content-free ledger)**: the ledger schema and write paths are unchanged;
  the R2 guard test settles a call with no content.
- **INV-1 to INV-9**: ledger code is unchanged since R1. `test_budget_ledger.py` passes 60/60.
  The new breaker probes confirm that a status-class refusal is settled once (`open_calls == 0`)
  and trips exactly for `TRIP_ERROR_CLASSES`.
- **Default local profile**: byte-identical parity transcript (§6), default composition →
  `OpenAICompatibleChatModel`, and `test_default_request_golden` passes 6/6. `llm.py` and
  `main.py` are unchanged since R1.
- **Governance**: R2 changes no `docs/` file. `7d6a31a..HEAD` under `docs/` is additions only
  (+76/−0). D-091 (`DECISION_LOG.md:1110`) is headed **PROPOSED**, with `Status: PROPOSED … Not
  accepted`, and needs the owner's acceptance of X1–X9 before merge. ADR-012 Amendment 3
  (`ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md:507`) is **PROPOSED**, `Not accepted`. D-090 and
  Amendment 2 remain reserved for PR #114. Phase B is stated as not authorised, and Q-013 is
  required beyond synthetic data.
- **No secret tracked**: §6.

## 8. Readiness

- **`pre_pr_check.py`: READY** to run on the committed, clean `e0d45d4` and its checklist. It
  needs owner authorisation, and this gate did not run it.
- **Publication** still needs explicit owner authorisation and the owner's decision on D-091
  X1–X9 / Amendment 3. R2-1 is Low and optional. If it is fixed before merge, that delta needs
  a fresh independent review.
- **Optional owner action:** run the `run_e2e.py` harness on a machine with Docker and
  Tesseract.
- **Phase B: BLOCKED.** There is no endpoint record, and the plan §15 prerequisites remain
  open. This gate authorises no remote activity.

## 9. Independence and writes

- This review was independent. The reviewer did not author or remediate any reviewed content
  and changed none of it. There was no edit, stage, commit, amend, reset, stash, checkout,
  clean, fetch, push, PR or merge in the implementing worktree or the primary checkout. The
  worktree is still at `e0d45d4` with 0 changes. The primary checkout is at `1d03986` with the
  same 11 untracked entries. No other worktree, cache or process was touched.
- Reviewer-owned writes are all under
  `C:\Users\shane\AppData\Local\Temp\claude\C--Users-shane-Desktop-FYP-data-dividends-zero-touch-clm\2d3c2cf7-e655-4130-9752-539571292417\scratchpad\reqg2\`:
  - `snap\`: the clone, including git-ignored test artefacts;
  - `mid\`: the `ee8a658` archive;
  - `base\`: a copy of the base archive;
  - `probes\`: probe sources and the scanner copies;
  - `out\`: JUnit, logs, parity transcripts;
  - this report.
