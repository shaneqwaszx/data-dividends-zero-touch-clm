# AI Assistant final validation evidence (B1-B, B2, B3) - 2026-10-31

Sanitised record of the offline validation of the AI Assistant completion programme. Evidence
class: **Local / offline** (disposable ledgers and databases under temporary folders, fakes for
the CLM backend and for Claude). No paid call, Test connection, qualification, activation,
reconciliation, service restart, live-store read or write, push or PR was made. No credential,
workspace or ledger identifier, machine path, case data or answer text is recorded here.

## 1. Branches (local commits only)

| Branch | Base | Content |
|---|---|---|
| `feat/b1b-hr-reconciliation` | `origin/main` 11d2202 | D-110 backend (PR-1a), QG remediation, HR reconcile form (PR-1b), D-110 records, real-Chromium E2E |
| `feat/b2-assistant-quality` | `origin/main` 11d2202 | Claude benchmark harness (cherry-picked with `-x`), B2-0 measurement tools and gate, D-111 (PROPOSED) |
| `feat/b3-final-validation` | B1-B head, merging B2 | integrated candidate (D-110 before D-111 in the decision log), this evidence and the UAT matrix |

## 2. Status vocabulary

PASS, FAIL, NOT EXECUTED (with the reason), KNOWN BASELINE FAILURE (only the 14 Errno 24 tests
named below, which fail with "Too many open files" on this Windows machine and pass alone, and
the `test_knowledge_answers` Chroma flake, which must pass alone), EXPECTED STARTUP-STORE CHANGE
(only `knowledge.sqlite3` bytes and Chroma `acquire_write` +1 at an assistant start).

## 3. Results

| Check | B1-B | B2 | Integrated (B3) | Status |
|---|---|---|---|---|
| Qualification basis | `5dc26b296026…` | `5dc26b296026…` | `5dc26b296026…` | PASS (unchanged) |
| Synthetic boundary `--check` | current | current | current | PASS |
| Full assistant suite | 3117 tests: 3103 pass, 14 Errno 24 | 3078 tests: 3064 pass, 14 Errno 24 | 3159 tests: 3145 pass, 14 Errno 24 (rerun on `ed3f845`, see section 5) | PASS with KNOWN BASELINE FAILURE (the same 14 on all three) |
| D-110 suite `test_claude_reconciliation_hr.py` | 81 pass | — | pass | PASS |
| Frontend vitest | 1305 / 1305 | — | 1305 / 1305 | PASS |
| Frontend typecheck and production build | pass | — | typecheck pass | PASS |
| Browser E2E (real Chromium): D-110 reconcile form, assistant streaming, answer records | 2 / 2 | — | 3 / 3 | PASS |
| Full lifecycle E2E (`scripts/run_e2e.py`) | — | — | — | NOT EXECUTED: needs a disposable `mongo:7` (Docker daemon not running) and Tesseract on PATH (absent); starting them was out of scope |
| Retrieval, degraded mode (no embedding model), RM / HR / Support | — | recall@3 0.96 with past cases, correct "nothing" 1.00 | gate passes | PASS |
| Retrieval, semantic mode | — | — | — | NOT EXECUTED: the local embedding model is not running and shares the live assistant's endpoint |
| Service overhead around an instant fake Claude | — | median 81.6 ms, p95 95.0 ms | — | PASS (measured) |
| Answer-quality targets after D-111 | — | — | — | NOT EXECUTED: needs D-111 approval and paid re-scoring |
| Restart and persistence on the running deployment | — | — | — | NOT EXECUTED: needs an owner-approved restart |
| First live HR reconciliation, cost and Console drift | — | — | — | NOT EXECUTED: needs S1–S3, the P1 attestation, rollout and the owner |

Known baseline failures (identical set on every branch):
- `test_model_factory::test_the_suite_guard_blocks_remote_connections`
- `test_phase_b_live::test_marker_is_not_an_offline_transport`
- `test_required_p2::test_real_http_sse_framing` (5 cases)
- `test_streaming_resources::test_loopback_total_deadline` (5 cases)
- `test_streaming_resources::test_real_chunked_http_enforces_budgets` (2 cases)

## 4. Independent reviews

| Review | Content | Verdict |
|---|---|---|
| Design QG rounds 1 to 4, rev-7 delta, rev-8 delta | D-110 specification | FAIL, PASS WITH NOTES, FAIL (M1), PASS WITH NOTES, FAIL (test list vs Q12), PASS WITH NOTES; every finding closed in rev 9 |
| PR-1a implementation QG | `bf3151b` | FAIL: H1 (the script's guard failed open when the profile read was busy, giving a false applied), M1 (stale marker not clearable by owner close), M2 (missing tests), Lows |
| PR-1a re-QG (fresh reviewer) | `2d9eff0` | PASS WITH NOTES; two wording Lows applied in `7d381a2` |
| Final integrated QG (fresh reviewer) | `ed3f845` | PASS WITH NOTES (one Medium on this record, since fixed; Lows L1 to L5 applied); see `.ai-pipeline/reports/AI_ASSISTANT_FINAL_QG.md` |

## 5. Integrated full suite

The first integrated run stalled at 22% inside asyncio's Windows socket-pair emulation during
event-loop setup (an unrelated evaluation-harness test; no progress for 10 minutes, the known
pattern on this host) and was stopped by its watchdog: ENVIRONMENT-BLOCKED, not a defect. The
rerun on `ed3f845` completed: 3159 tests, 3145 passed, 14 failed, all with "Too many open
files" and exactly the set named in section 3 (identical to the B1-B and B2 runs). Later
commits change only page wording (re-verified: vitest 135 / 135 for the page, typecheck, the
reconcile E2E) and a script docstring; the assistant suite was not rerun for them.
