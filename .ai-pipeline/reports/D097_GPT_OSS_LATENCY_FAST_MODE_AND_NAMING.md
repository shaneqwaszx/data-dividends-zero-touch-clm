# D-097 GPT-OSS 120B latency, Fast configuration, progress UX and naming — evidence

Branch `claude/gracious-lovelace-bjvh2z` restarted from main `025ebc7` (PR #126 squash-merged).
No real or paid OpenRouter call was made. All timings below are **offline**: the real assistant
app under uvicorn on loopback, the test suite's fake CLM backend, and a timed **mock**
OpenRouter (`apps/assistant/scripts/benchmark_chat_latency.py`). Provider delays are scenario
inputs. Mocks cannot measure GPT-OSS itself, nor how Low reasoning changes its speed or answers.

## 1. Where the time goes

**Real evidence (Phase B live run, 17 turns, GPT-OSS 120B Medium on `deepinfra/bf16`,
`AI_ASSISTANT_PHASE_B_LIVE_EXPERIMENT.md`):** total p50 12,437 ms / p95 30,218 ms; first shown
line p50 12,078 ms / p95 28,250 ms. First line ≈ total: visible text starts only after the
hidden reasoning. A least-squares fit of total ms on completion tokens gives about 1,208 ms
fixed + 17.1 ms per token (R² 0.76, ≈ 58 tokens/s); about 90% of the time is token generation,
and reported reasoning tokens track completion tokens (R² 0.99).

**Offline stage breakdown, `medium_like` scenario** (calibrated on that fit: 10.5 s before
visible content, then 58 tokens/s; 15 questions, Garden case, D-095 verified):

| Stage (p50) | ms | Share of time to first displayed line |
| --- | --- | --- |
| Case retrieval (3 CLM backend reads) | 26.8 | |
| Document digests (1 read) | 8.6 | |
| Synthetic eligibility check | 1.2 | |
| Model readiness (warm: earlier calls verified) | 2.6 | |
| Budget admission (ledger transaction) | 2.0 | |
| **Everything before the provider request** | **64.7** | **0.6%** |
| Provider prefill + hidden reasoning → first model text | 10,667 | 94.6% |
| Exact-line guard: first model text → first displayed line | 545 | 4.8% |
| First displayed line → final answer | 1,286 | |
| Post-answer verification (background, after the answer) | 157 | — |

The total is 12,564 ms, against 12,437 ms measured live. Real backend handler times, measured
in-process on the memory-mode backend for a synthetic Garden case: `/me` 2.6 ms, case 16.4 ms,
documents 4.8 ms, digests 4.0 ms (p50, 200 reads).

**Primary bottleneck: provider-side hidden reasoning before the first visible token** (about
95%). Application overhead is about 65 ms. The exact-line guard's wait for the first complete
line (about 0.5 s at 58 tokens/s) is a required safeguard (no unvalidated text is shown).

## 2. Scenarios, baseline vs optimized (identical conditions; p50/p95 ms; 30 questions each)

| Scenario | Metric | Baseline (main) | Optimized (this branch) | Δ p50 |
| --- | --- | --- | --- | --- |
| fast_warm (Garden) | first model text | 421.6 / 437.4 | 420.3 / 431.7 | −0.3% |
| | first displayed line | 586.9 / 602.0 | 586.6 / 598.3 | −0.1% |
| | total | 977.4 / 991.5 | 978.0 / 991.2 | +0.1% |
| fast_warm_multiple_owner | first displayed line | 582.7 / 594.9 | 582.2 / 597.9 | −0.1% |
| fast_cold_preflight | first displayed line | 737.7 / 754.5 | 739.5 / 758.2 | +0.2% |
| slow_warm (3 s reasoning, 50 tok/s) | first displayed line | 3,776.5 / 3,791.1 | 3,773.5 / 3,793.6 | −0.1% |
| long_prompt (6 history turns) | first displayed line | 782.0 / 795.7 | 778.9 / 793.3 | −0.4% |
| multi_line_answer (6 lines) | total | 1,144.7 / 1,163.8 | 1,141.0 / 1,171.7 | −0.3% |
| newline_delay (0.4 s per line break) | first displayed line | 984.8 / 998.6 | 981.2 / 990.6 | −0.4% |
| concurrent_3 | total | 165.9 / 1,074.5 | 183.9 / 1,086.5 | noise* |
| **followup_pending_verification** (asked at once; metadata 3 s late) | first model text | 5,467.4 / 5,472.2 | **3,570.1 / 3,573.3** | **−1,897 ms (−34.7%)** |
| | first displayed line | 5,632.0 / 5,645.3 | **3,734.0 / 3,737.2** | **−1,898 ms (−33.7%)** |
| | total | 6,022.8 / 6,042.7 | **4,123.1 / 4,132.8** | **−1,900 ms (−31.5%)** |
| medium_like (15 questions) | total | 12,564.0 / 12,573.7 | 12,563.4 / 12,587.6 | 0.0% |

\* concurrent_3: in both runs 30 questions answered by the model and 60 by case data (the
default `AI_ASSISTANT_BUDGET_MAX_IN_FLIGHT=1` admits one remote call at a time); the p50 is a
case-data reply under thread scheduling.

Fail-closed scenarios (unchanged by this branch):

- **provider_timeout** (1.5 s limit, 3 s stall): the first question falls back to case data at
  1,748 ms. The timed-out call has no generation reference, so verification quarantines it and
  the ledger breaker opens: every later question gets the case-data answer (about 63 ms) until
  an operator reconciles.
- **cancelled_stream** (the client closes after the first line, as when the RM switches case
  mid-answer): the same happens, because a cancelled call settles with no generation
  reference: 1 cancelled, then 9 case-data answers.

## 3. Changes and their measured effect

| Change | File (qualification basis?) | Effect |
| --- | --- | --- |
| Generation metadata read every second for the first 10 s, within the caller's unchanged 120 s bound | `openrouter_account.py` (not in the basis) | −1.9 s (−34%) for a follow-up asked while the previous call's verification waits; at most 8 more free metadata reads per verification; no other scenario changes |
| Progress stages and "What this answer used" | frontend | Perceived responsiveness only (real events); no latency change |
| Model naming | `model_catalog.py` (not in the basis), frontend | Display only |
| Optional Fast (low reasoning) configuration | `model_catalog.py`, `model_admin.py`, `assistant_eval/qualification.py`, `config.py` (none in the basis) | Off by default; needs its own paid qualification |

Rejected for lack of value: parallelising the three CLM backend reads (about 24 ms
sequential; under 10 ms saving against a 12.4 s median).

## 4. Medium vs Low vs 20B (assessment; no paid comparison was run)

| | A. 120B Medium (current) | B. 120B Low (Fast) | C. 20B Low (comparison only) |
| --- | --- | --- | --- |
| Model / endpoint | `openai/gpt-oss-120b`, `deepinfra/bf16` | same | `openai/gpt-oss-20b`: endpoint, price, quantization and ZDR status **unknown** (not fetched; not authorised) |
| Reasoning tokens (median) | 704 (measured) | lower, amount **unknown** | unknown |
| Latency p50 | 12.4 s (measured) | projection: 9.8 s / 7.3 s / 4.8 s if reasoning falls 25% / 50% / 75% (fit above; offline `low_projection_half_reasoning` scenario: 7.3 s total, 6.0 s first line) | unknown |
| Time to first line | ≈ total (reasoning first) | falls with reasoning (same mechanism) | unknown |
| Throughput | ≈ 58 tokens/s (fit) | same endpoint, same rate expected | unknown |
| Cost per question | US$0.000223 median (measured) | projection about US$0.000170 at −50% reasoning; prompt alone about US$0.000113 | unknown |
| Answer-quality risk | line validity 0.868, 2/17 fallbacks, 0 unsafe (not human-scored) | possibly more wrong-line choices or paraphrases (withheld by the guard → more fallbacks, not unsafe display); size unknown | higher risk; unknown |
| Qualification | current (basis `2bd93aeb8886…`, fingerprint unchanged) | its own fingerprint and qualification (paid) | not offered |

Sources: OpenAI gpt-oss README ("Configurable reasoning effort: … low, medium, high … based on
your specific use case and latency needs") and harmony guide ("By default, the model will do
medium level reasoning"); OpenRouter reasoning documentation as recorded in
`AI_ASSISTANT_OPENROUTER_120B_INVESTIGATION_20261026.md` (reasoning tokens billed as output,
count against `max_tokens` on most providers; `exclude: true` still reasons). openrouter.ai and
openai.com were not reachable from this session, so endpoint data dates from 2026-10-26. There
is no official "GPT-OSS 120B Instant" model.

## 5. Qualification compatibility

`qualification_basis()` is `2bd93aeb8886bdf431f8a910555c955e57318934ada8746f484c18746ec6295c` at
main and on this branch. No `BASIS_FILES` entry changed, and `synthetic_boundary.json` stays
current (`build_synthetic_boundary.py --check`): the new labels are kept out of
`ai_assistant/*.py` string constants. The Balanced entry keeps its profile id and
`remote_fingerprint`; the stored activation needs nothing. Fast (`openrouter_gpt_oss_120b_low`)
has its own fingerprint and has no qualification.

## 6. Not implemented (each changes a qualification-basis file: paid requalification of Balanced, and of Fast if used)

1. Record the generation reference from the first stream chunk (`llm.py`/`openrouter.py`/
   `budget.py`), so a cancelled or timed-out call can still be verified instead of opening the
   breaker.
2. Server-side stage events in the NDJSON stream (`main.py`), for finer progress (readiness vs
   provider).
3. Refresh the preflight in the background before it expires (`remote_test.py`), removing the
   cold-preflight cost (about 150 ms here; network-dependent).
4. Verification cadence constants (`remote_checks.py`); partly covered by the early metadata reads (section 3).

## 7. Owner decisions before a paid comparison

- Approve a bounded paid A/B (for example the 17 Phase B questions × Medium and Low, one rep,
  under US$0.01 at measured prices), with T7 approval, enabling Fast and qualifying it.
- Decide whether 20B is ever evaluated (endpoint, ZDR and price must be checked first).
- Decide whether the basis-file improvements in section 6 justify a requalification.

## 8. Independent Quality Gate

- **R1 FAIL**, one REQUIRED finding: "What this answer used" said a case-data answer was "this
  case's data only", although the no-AI answer can add approved guidance, and it counted
  every retrieved source rather than the cited ones. Advisories, left as they are and recorded
  here:
  - the early metadata reads change a cadence that a basis file's comment describes (outcome
    identical whenever metadata is published within the 120 s bound; up to 8 more free reads;
    a non-404 reply such as a rate limit fails closed, as before);
  - `generation()` edge cases with zero or inexact waits (no caller passes them);
  - Fast is kept apart from Balanced by profile id (the fingerprints would coincide only if
    the configured effort were already low, when Fast is not listed);
  - the second progress stage also shows briefly when no model will be used.
- **Remediation:** the case-data line now reads "No AI model wrote this answer: it comes from
  this case's data and any approved guidance cited", and the count is "Approved sources
  cited", counting cited sources only (tests added).
- **R2 PASS** on the remediated content: both assertions fail without the fix, and the other
  19 files are unchanged. R1 also reproduced the benchmark (follow-up first line 5,629.8 →
  3,732.7 ms at p50, 5 questions) and confirmed that the basis hash, Medium's fingerprint and
  Fast's isolation hold. This section was added after the review; it changes no reviewed file.
