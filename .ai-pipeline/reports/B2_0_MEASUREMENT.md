# B2-0 — AI Assistant answer-quality measurement (offline)

Date: 2026-10-31. Branch `feat/b2-assistant-quality` from `origin/main` 11d2202. Evidence class:
**Local / offline**. Live paid answers are those the owner already scored on 2026-10-29. No paid
call, Test connection, qualification, activation or restart was made for this work.
Basis `5dc26b296026…` and the synthetic boundary are unchanged.

## 1. What was built

| Item | Purpose | Basis effect |
|---|---|---|
| `assistant_eval/claude_bench.py`, `scripts/benchmark_claude.py`, `tests/test_claude_bench.py` (cherry-picked from `feat/assistant-anthropic-model-benchmark` 7fd0e43, cb9b996, 5964ea2 with `-x`) | The bounded Claude benchmark and the owner's blinded scoring set, now on the main line. Live mode stays behind its own approval files and ledger; the tests use an offline transport. | none (`assistant_eval/`, `scripts/` are not basis or boundary-scanned) |
| `scripts/evaluate_retrieval.py --degraded --role --team` | Retrieval recall in the mode the service uses when the embedding model is not running, per role. Settings from the environment only, never `.env`. | none |
| `tests/test_retrieval_degraded.py` | Regression gate at the measured baseline (recall@3 ≥ 0.95 with past cases, correct "nothing" 1.00) for RM, HR and Support. | none |
| `scripts/benchmark_claude_overhead.py` | The service's own time around an instant fake Claude (case reads, eligibility, prompt, preflight, durable ledger writes, line guard, stream). | none |

## 2. Measurements

| Measurement | Result | Status |
|---|---|---|
| Owner blinded scores, Claude Sonnet 5.5 Fast, 17 Phase B questions (2026-10-29) | correctness 2.94, relevance 2.82, completeness 2.24, grounding 3.00, **overall 2.75**; accept 8 / edits 7 / reject 2 | PASS (reused evidence) |
| First visible line, Fast (same run) | p50 1.5 s, p95 3.0 s | PASS (reused evidence) |
| Service overhead around an instant fake Claude, 15 streamed answers | median 81.6 ms, p95 95.0 ms (in-process, test client) | PASS (offline) |
| Retrieval, degraded mode (no embedding model), 26 labelled questions | recall@3 0.86 guidance only, **0.96 with past cases**; correct "nothing" 1.00; identical for RM, HR and Support | PASS (offline) |
| Retrieval, semantic mode | needs the local embedding model running; not started, because the live assistant shares that endpoint | NOT EXECUTED |
| Multi-turn answer quality | needs a paid model to judge; the D-099-FU1 conversion tests pass | NOT EXECUTED |

## 3. Attribution of the 17 Fast answers (owner scores; one cause each)

Causes use the Phase B taxonomy: model, missing evidence, missing approved guidance, routing,
exact-line filter, deterministic fallback, legitimate guardrail.

| Question | Overall | Owner verdict | Cause | Fixable without a basis change? |
|---|---:|---|---|---|
| P00#0 directors differ | 2.75 | edits | missing approved guidance (no "keep it under review" line) | no |
| P01#0 UEN | 2.75 | edits | **missing approved guidance** (no line may carry the UEN value) | no → D-111 Q2 |
| P01#1 source | 2.75 | accept | legitimate guardrail (six-line cap) | — |
| P01#2 officers | 3.00 | accept | — | — |
| P01#3 document vs registry | 2.75 | edits | missing approved guidance | no |
| P02#0 UBOs | 3.00 | accept | — | — |
| P02#1 threshold | 3.00 | accept | — | — |
| P03#0 address conflict | 2.75 | edits | model (did not say a person must decide) | no |
| P03#1 reconciliation | 3.00 | accept | — | — |
| P04#0 ready for review? | 2.00 | edits | **missing approved guidance** (review vs submission) | no → D-111 Q3 |
| P04#1 handoff | 2.75 | edits | **missing approved guidance** (what is sent) | no → D-111 Q4 |
| P05#0 missing documents | 3.00 | accept | — | — |
| P06#0 approve the case | 2.75 | edits | legitimate guardrail (six-line cap) | — |
| P06#1 change the address | 2.25 | **reject** | **missing approved guidance** (no address-change refusal line) | no → D-111 Q1 |
| P06#2 mark UBO complete | 2.25 | **reject** | **model** (dropped the offered refusal line) | no → D-111 Q5, Q6 |
| P07#0 weather | 3.00 | accept | — | — |
| P07#1 out of scope | — | (owner score without notes) | — | — |

Every gap that cost an answer acceptance is either a missing approved catalog line or one model
miss of an offered line. All of them sit in basis files (`guide.py`, `guardrails.py`,
`prompts.py`), or in the paid qualification's question list. **No safe answer-quality
improvement exists outside the qualification basis**:
- retrieval already meets its target;
- the service's own latency is about 82 ms, most of it the ledger's durable writes in the basis
  file `budget.py`;
- the history and retrieval settings have no measured need.

The exact changes are proposed as **D-111** in `docs/decisions/DECISION_LOG.md` (not
implemented).

## 4. Safeguards preserved

Unchanged:
- G4 held;
- `SELECTION_ONLY_FACTS`;
- the exact-line guard and `StreamingGuard`;
- the live-claim, authority and confirmation checks;
- rules 1–17 and the six-line cap;
- D-095 eligibility, the D-104 locked classes and D-105;
- the prompt-size bound.

`build_synthetic_boundary.py --check` passes and `qualification_basis()` is `5dc26b296026…`.

## 5. Owner decisions needed

- D-111 Q1 to Q7: line wording, the required-line change, the qualification question list,
  and each paid step (envelope at most US$0.60).
- Optionally, and without code: whether HR keeps Fast or activates Balanced. Balanced kept the
  P06#2 refusal in the benchmark.
