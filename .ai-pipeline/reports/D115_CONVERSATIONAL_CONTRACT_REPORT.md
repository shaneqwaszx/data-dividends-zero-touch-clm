# D-115 X2 — Conversational answers for external models (synthetic-only contract)

Owner direction: "PRIORITY CORRECTION — Deliver Conversational AI, Not More Planning"
(2026-11-04). Decision rows: D-115 X2, X3, C8 in `docs/decisions/DECISION_LOG.md`.

Status: owner-approved for PR publication (D-115 X4, 2026-11-05), branch
`feat/d115-conversational-external` on main `92516a5`; draft PR, not activated. Conversational answers stay OFF until the owner records
approval (`config.CONVERSATIONAL_DECISION`, a reviewed constant, `None` here). Evidence class:
Local (mock Anthropic and OpenRouter APIs, synthetic fixtures, disposable stores, no paid call,
US$0 spent).

This supersedes the held answer-side extraction (`d115-answer-side-20261105`, QG9 FAIL). Its
answer-side checks are included here, with the QG9 findings fixed (C8). The failed scope-gate
candidate (`d115-copilot-scope-20261104`) and the D-118 PR #157 worktree are untouched.

## 1. What changed

| Area | Change |
| --- | --- |
| `config.py` | `answer_mode`: `auto` (new default), `exact_lines` (rollback), `copilot` (forced; local model only unless approved). `conversational()` and `external_conversational()`: the latter needs `CONVERSATIONAL_DECISION`, never a setting alone. No new env var, HR field or switch. |
| `main.py` | `copilot_for`: local model when conversational; external model only when the owner's decision is recorded **and** it is in D-095 development mode. The copilot branch runs `remote_gate` (unchanged D-095 per-call eligibility check + single-use ticket) on the exact copilot prompt; refused → case-data answer, nothing sent, reason `remote_boundary` recorded. External models never get the ownership analysis (`local_ownership`). `check.usable`. General chat stays local-model only. |
| `copilot.py` | Arithmetic-only questions ("What is 1+1?") refused before any call; `status_problem` sentence check. |
| `claims.py` | Status-claim checks + C8 (conditions/time clauses, "next stage", "nothing", in-match negation). |
| `model_catalog.py` | X3: conversational fingerprint for external entries once approved; `exact_lines` restores the old identity. |
| `model_qualification.py`, `assistant_eval/*` | Conversational qualification answers as the chat will (service answer mode and D-095 decision; harness model shows the external flag; eval case document = tracked Garden fixture with real SHA-256). Exact-line qualification unchanged. |
| `telemetry.py`, `runner.py` | `off_domain` fallback reason; runner records refused turns; conversational turns not line-mapped. |
| `scripts/build_synthetic_boundary.py`, `synthetic_boundary.json` | Comment corrected; regenerated (+aiassistantsettings, +conversational, −restricts, −unrestricted). |
| `anthropic_chat.py` | Unchanged (an earlier prompt-shape widening was withdrawn with the ownership fix). |

## 2. Controls (tested)

- External calls only for verified synthetic cases in D-095 mode. A non-synthetic company
  sends nothing (all three external configs). D-094-only GPT-OSS keeps exact lines. The
  adapters still refuse any call without a ticket. Follow-up history passes the D-095 text check.
- `AI_ASSISTANT_ANSWER_MODE=copilot` alone keeps external models on exact lines.
- External prompts never carry the ownership analysis.
- Unrelated questions ("What is 1+1?", "When is Independence Day?") never reach the model.
- These are all removed: an invented GoldTier status, an approval claim, and a prompt-injection
  "address now matches / blockers resolved / ready for GoldTier". An action request gets the
  read-only line.
- An exact-line qualification never counts for conversational answers, and rollback restores it.
- Calls are charged to the D-118 session (+1 chat call, committed spend rises).
- Before approval nothing changes: same question → exact lines, no conversational prompt.

## 3. Requalification

Basis: main `17a3172e1607…` → `49bc0541fa40…`. Every qualification on main's basis becomes
stale. Once approved, each external configuration to be used needs a conversational
requalification (2 approved questions each, ~2 paid calls): Claude Sonnet 5.5 Balanced and Fast,
GPT-OSS 120B Balanced and Fast; plus the local model (free).

## 4. Tests and review

- New: `tests/test_conversational_external.py` (Claude Balanced/Fast and GPT-OSS, stream and
  non-stream; controls above), `tests/test_answer_side_checks.py` (status claims incl. QG9/QG10).
- Affected suites (conversational, answer-side, claims, copilot, Claude runtime, remote test,
  synthetic eligibility, Claude HR enablement): all pass.
- Full assistant suite: 3,560 tests, 14 failures. All 14 are loopback-socket timing tests
  (`test_streaming_resources`, `test_required_p2::test_real_http_sse_framing`, suite-guard
  tests). They pass when run alone, and a full run of untouched main fails the same 14 tests:
  an environment issue on this machine, not this change.
- D-118 compatibility (PR #157 head `c80fdac` + this final diff): Playwright "D-118 Set up AI"
  6/6 pass (scenarios A–H). D-118, conversational, remote, Claude and eligibility suites all pass.
- ruff and mypy clean. The formatting state of changed files equals main's.
- Independent QG: FAIL (2 HIGH, 3 MEDIUM), remediated once. Delta QG: **PASS WITH NOTES**.

## 5. Limitations and approvals needed

- **Owner security/data-boundary approval of X2** (set `CONVERSATIONAL_DECISION` in a reviewed
  change), then paid requalification spend.
- External conversational answers only in D-095 development mode on verified synthetic cases. A
  case whose documents are not tracked fixture files gets the case-data answer.
- External models get no ownership analysis, so UBO-detail questions are answered without
  ownership figures (sentences naming holdings are removed). The local model keeps it.
- Claude is streaming-only, as before. Non-streamed `/chat` gives the case-data answer.
- Mocked answers prove the pipeline, not real answer quality; that is measured only by the
  paid requalification.
- The two readiness phrasings from the delta review were corrected after owner approval (C9).
  The sentence checks are pattern-based. Other unusual phrasings of an invented status can still
  pass; real-provider answers have not been measured.
- Hosted CI has been billing-blocked on recent PRs; local evidence only.

## 6. Shortest path to a demo

1. Owner approves X2; the change sets `CONVERSATIONAL_DECISION`, then commit → PR → merge.
2. Restart the assistant service (owner).
3. AI Models: select model → enter API key → Qualify (2 paid calls, existing D-118 session) →
   Activate.
4. Open a verified synthetic case (Garden with the tracked fixture document, Mock ACRA) and chat.
