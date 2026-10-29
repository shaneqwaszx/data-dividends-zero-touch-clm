# D-099-FU1 Quality Gate — Claude multi-turn compatibility

Independent reviewer (fresh agent, not the implementer), 2026-10-29. Saved verbatim in
substance by the coordinator (subagents cannot write files).

**Verdict: PASS**

## Frozen identity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\assistant-claude-sonnet-console-20261029`,
  branch `feat/assistant-claude-sonnet-console` (draft PR #130).
- Reviewed commit `b7a5ca60d5748647236a662e0773005a32df28a7`, tree
  `624a63deee92cbb76c6cf67e20410a0e74091bb2`, parent `e63ff311` (D-099 Option B, QG R3 PASS).
- Delta `git diff e63ff311 b7a5ca6`: 8 files: code `anthropic_chat.py`, `anthropic_runtime.py`
  (comment only); tests `test_claude_multi_turn.py`, `fixtures/eval/claude_multi_turn.json`;
  docs DECISION_LOG C10, AI_MODEL_CONFIGURATION.md, PROJECT_STATE.md,
  `.ai-pipeline/reports/D099_FU1_MULTI_TURN.md`.
- Reviewer made no edits, staging, commits or branch changes; no `.env`, network, provider or
  Mongo access.

## Commands (from `apps/assistant`, `PYTHONPATH=.`, venv Python)

| Command | Result |
| --- | --- |
| pytest test_claude_multi_turn, test_claude_console, test_claude_runtime, test_synthetic_eligibility, test_remote_test, test_model_management | 366 passed (110.9 s) |
| pytest test_phase_b_live, test_eval_harness, test_guardrails, test_budget_guard | 139 passed |
| `ruff check .` / `ruff format --check .` | clean / 129 files formatted |
| `mypy ai_assistant assistant_eval` | no issues (56 files) |
| `scripts/build_synthetic_boundary.py --check` | current |
| `qualification_basis()` | `33f602653de73f372a787a9d4403daedcd589140aae02b86a4796cd994e87513` (matches) |
| `git diff --quiet e63ff311 b7a5ca6 -- '*gold*.json'` | unchanged |
| `git diff --check e63ff311 b7a5ca6` | clean |
| inline adversarial probes of `system_and_conversation` | see below |

Full suite not rerun by the reviewer (implementer: 2,837 collected, 2,823 passed, 14 Windows
Errno 24 passing in isolation, run before the final prefix tightening); every Claude/Anthropic
test file was rerun on the final content.

## Adversarial review

- Browser history cannot become a system block: `ChatTurn.role` is
  `Literal["user","assistant"]` with `extra="forbid"` (`main.py:110-114`); `history_of` and
  `trim_history` copy role/content only; only `prefix_messages` and `build_messages` produce
  system messages.
- A user/assistant turn starting with a marker is never promoted: `_question_block` is applied
  only to `role == "system"` (probe confirmed).
- Marker fidelity: all three starts match `knowledge_answers.py:114`, `prompts.py:550`,
  `prompts.py:605`; order knowledge → topic → terms matches `build_messages`.
- Shape strictness: refused — history ending with user, 3rd unknown leading system, empty or
  bare `QUESTION TOPIC:` block, duplicated knowledge, blocks split around history, fewer than
  two leading messages. First turn `[S,S,K,T,C,user]` accepted as produced.
- Every Claude path uses the two-message prefix (chat, remote qualification through the
  service; connection check is a no-inference preflight). The one-system `PROBE` and
  `typical_reservation` are GPT-OSS paths only.
- Ticket/admission binding: `_ready` and `_admit_in_adapter` decide on the canonical list;
  `payload()` converts only at serialisation; role classes are kept, so the boundary's
  role-based vocabularies apply to the role each text is sent with — no widening. A
  pre-converted list holds no ticket (tested).
- Refusal before spend: shape refused in `_ready` before readiness, key, ledger, preflight or
  reservation; adapter `_admit` refuses again before any request (tested: no requests,
  `last_call_id()==0`, breaker closed; ticket for an invalid shape sends nothing).
- Unchanged: pinning, workspace check, reservation (canonical bytes), G-8, ledgers, no
  automatic switch, GPT-OSS payload (tested canonical), exact-line guard on every turn
  (tested), no prompt/key text in logs (tested).
- Test quality: exact payload equality for Balanced and Fast, order/no-drop checks, 29
  refused shapes, runtime settle/verify, real-service 12-turn MOCK runs (8 follow-ups), RM
  journey after HR activation with 0 OpenRouter calls; fixture synthetic, test-only, outside
  `BASIS_FIXTURES`.

## Findings

- Critical / High / Medium: none.
- Low L1 (evidence freshness): the full-suite run predates the prefix tightening; mitigated by
  the reviewer's 505 focused passes on `b7a5ca6`. Not blocking.
- Info I1: DECISION_LOG C10 does not spell out "exactly two leading prefix messages when
  history is present (at least two otherwise)"; the FU1 report does. Optional.
- Info I2 (pre-existing): a non-alternating history or one ending with a user turn is refused
  for Claude (case-data answer) while GPT-OSS accepts it; fail-closed, unchanged by FU1.
- Info I3: Claude sees per-question blocks before the history; follow-up answer quality is
  unmeasured until a paid, separately approved qualification (documented).

## Required fixes

None.

## Change classification

API/type, schema, configuration, business rule, mapping, architecture, provider status:
unchanged. Connector: Anthropic request shaping only (Mock/offline). Auth/security: stricter
shape validation, no weakening; boundary vocabulary unchanged. Runtime: Claude follow-ups now
sent after the same admission, reservation and preflight. Basis `adec795f61bd…` →
`33f602653de7…`.

## Git status

Worktree clean at `b7a5ca6`; reviewer changed nothing. Next action is the owner's; no paid
qualification or activation without separate approval.
