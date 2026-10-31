# AI Assistant final UAT and validation matrix (B3)

Date: 2026-10-31. Scope: the AI Assistant (Claude Sonnet 5.5 Fast active), the HR AI Models
Console including D-110 reconciliation, and the RM and Support assistant surfaces. Evidence
class: **Local**. Status vocabulary: **PASS**, **FAIL**, **NOT EXECUTED** (with the reason),
**KNOWN BASELINE FAILURE** (only the 14 named Errno 24 tests in
`docs/evidence/AI_ASSISTANT_FINAL_VALIDATION_2026-10-31.md` section 3 and the `test_knowledge_answers`
Chroma "Nothing found on disk" flake, which must pass alone), and **EXPECTED STARTUP-STORE
CHANGE** (only `knowledge.sqlite3` bytes and Chroma `acquire_write` +1 at an assistant start).

Offline rows are executed by the automated suites named in the evidence column. Rows marked
*owner* need a person on the running deployment and are NOT EXECUTED until the owner approves
each step; none needs a paid call unless stated.

## HR (AI Models Console)

| # | Scenario | Expected | Evidence | Status |
|---|---|---|---|---|
| H1 | Claude ledger panel shows key alias, windows (SGT), baseline, kept overcount, estimate, calls | figures consistent; never the key | `test_claude_ledger_view.py`, `AiModelManagement.test.tsx` | PASS |
| H2 | Preview a Console reading (refresh time, three scopes) | before/after, drift, breaker warning, new windows; nothing written | `test_claude_reconciliation_hr.py`, frontend tests | PASS |
| H3 | Apply with the typed figure | applied; windows renew; cap and activation unchanged; run listed | same | PASS |
| H4 | Refusals: breaker open, open call, unverified or quarantined call, open run/marker, lower figure, ledger ahead > US$0.05, stale/future reading, call too recent, scopes, wrong typed figure, foreign or expired preview, no P1 attestation | each refused with its code and page text; nothing written | same | PASS |
| H5 | Concurrent CLI or ledger write between preview and apply | CONTROLS_CONFLICT; run refused; ledger unchanged | same | PASS |
| H6 | Interrupted apply then Resolve | applied only when proven, failed only when proven, otherwise unresolved; LEDGER_BUSY never decides | same | PASS |
| H7 | RM or Support calls any reconciliation route | 403 | same | PASS |
| H8 | First live HR reconciliation before 2026-11-07 09:42:37 SGT | applied; ledger, run and audit agree | *owner*: needs S1–S3, P1 attestation, rollout restart | NOT EXECUTED |

## RM

| # | Scenario | Expected | Evidence | Status |
|---|---|---|---|---|
| R1 | Case chat answered by Claude Fast on a synthetic case | model answer, exact-line guard, no unsafe line | `test_claude_runtime.py` (fake Claude) | PASS |
| R2 | Action requests (approve, change address, mark UBO complete) | never claims the action; refusal where a line exists | `test_phase_b_quality.py`, guardrail tests | PASS |
| R3 | Multi-turn follow-up | conversion keeps order; unknown shapes refused before reservation | `test_claude_multi_turn.py` | PASS |
| R4 | Stale reconciliation (> 7 days) | chat refused with the case-data answer | `test_claude_runtime.py` | PASS |
| R5 | Live paid RM answer on the running deployment | Claude-answered, verified, cost recorded | *owner*: paid call | NOT EXECUTED |

## Support

| # | Scenario | Expected | Evidence | Status |
|---|---|---|---|---|
| S1 | Chat without a case (D-105) and knowledge review list | works; no case data | existing Support tests | PASS |
| S2 | Reconciliation and model routes | 403 | `test_claude_reconciliation_hr.py`, `test_model_management.py` | PASS |

## Cross-cutting

| # | Check | Expected | Evidence | Status |
|---|---|---|---|---|
| X1 | Qualification basis | `5dc26b296026…` unchanged | `qualification_basis()` print | PASS |
| X2 | Synthetic boundary | current | `build_synthetic_boundary.py --check` | PASS |
| X3 | Full assistant suite | only known baseline failures | junit: B1-B 3117, B2 3078, integrated 3159 tests, each with the same 14 Errno 24 | PASS with KNOWN BASELINE FAILURE |
| X4 | Frontend suite, typecheck, build | pass | vitest, tsc, vite | PASS |
| X5 | Browser E2E for the reconciliation panel | pass in real Chromium | `e2e/ai-models-reconciliation.e2e.ts` (self-contained); the full `run_e2e.py` lifecycle needs Mongo and Tesseract | PASS (self-contained); full lifecycle NOT EXECUTED |
| X6 | Restart and persistence | fingerprints identical except expected start-up changes; activation, basis, ledger and runs intact | *owner*: restart | NOT EXECUTED |
| X7 | Cost: ledger total equals verified calls; Console drift ≤ US$0.05 | holds | *owner*: Console reading | NOT EXECUTED |
| X8 | Answer quality targets (D-111) | overall ≥ 2.85, completeness ≥ 2.60, rejects ≤ 1 | *owner*: D-111 and paid re-run | NOT EXECUTED |
