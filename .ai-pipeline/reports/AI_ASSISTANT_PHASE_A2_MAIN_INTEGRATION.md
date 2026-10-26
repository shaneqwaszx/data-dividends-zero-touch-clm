# AI Assistant Phase A2: latest-main integration (PR #116)

| Item | Value |
|---|---|
| Date | 2026-10-26 |
| Branch / PR | `feat/assistant-phase-a2-20261026-int` / PR #116 |
| Integration commit (merge) | `65c6cfa0aa7d2ab901e3d724d96ed26a24dcb529`, tree `e48fac1da5cf1ce9b6e4626b776719975366f5dc` |
| Parents | `c5b5f8a` (published PR head: reviewed product `e0d45d4` plus QG reports) and `06e6a9b81b59f631ddbcf5136cee9f1bf384df10` (`origin/main`, PR #114) |
| Previous base | `7d6a31a` (PR #113) |
| Remote activity / spend | No OpenRouter or other non-loopback request; US$0. `OPENROUTER_API_KEY` was never read, and test runs unset it |

## 1. Overlap inventory

- **Main's delta** `7d6a31a..06e6a9b`: 35 files.
- **A2's delta** `7d6a31a..c5b5f8a`: 31 files.
- **Shared files:** five.

| File | Textual conflict | Resolution |
|---|---|---|
| `apps/assistant/ai_assistant/main.py` | yes, the import block only | Combined A2's `llm` and `model_factory` imports with PR #114's `TopicPlan` / `topic_plan` import. Every other hunk from both sides auto-merged. Check: the +/- line sets of each side's delta are identical before and after the merge |
| `docs/decisions/DECISION_LOG.md` | yes, both append at the end | Main's D-090 first, then A2's D-091. Both stay PROPOSED and distinct. A2's "reserved by PR #114" sentence now reads "PR #114's, merged before this one". Nothing was removed from either side |
| `docs/decisions/ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md` | yes, both append at the end | Amendment 2 (D-090) first, then Amendment 3 (D-091), with the same sentence change. Nothing was removed |
| `apps/assistant/README.md` | no | auto-merged; both deltas preserved (same check) |
| `docs/ARCHITECTURE.md` | no | auto-merged; both deltas preserved (same check) |

**Semantic interactions checked**

- **`_model_reply`:** PR #114 applies `with_required_lines` inside it, after `outcome.selected(validation)`. So the telemetry and metrics that A2 extends count only the model's own selection; required lines are not credited to the model.
- **Eval runner:** `assistant_eval/runner.py` already excludes `added_lines` from model-selected lines. This file is main's and A2 does not touch it.
- **Answer records:** A2's `record_reason` ("budget_refused" counts as model unavailable) and PR #114's redacted `allowed_lines` / `chosen_lines` / `shown_answer` touch different statements, and both are kept.
- **Streaming:** PR #114's `streamed` tracking and A2's `outcome.reported(piece)` / `empty_content` sit side by side in the stream loop.
- **Composition:** the local model is still built through `build_chat_model(config, local_adapter=OpenAICompatibleChatModel)`. The default request is unchanged; see the parity row in section 3.

## 2. Integration-only change

There is one change, in tests only:
- `apps/assistant/tests/test_budget_guard.py`: `test_a_remote_answer_is_settled_at_its_reported_cost`.
- `apps/assistant/tests/test_openrouter_adapter.py`: `test_a_remote_answer_through_the_service_records_content_free_v2_metrics`.

**Why they failed:** both expected the answer to equal the model's single line. Under D-090, the service now adds the topic's required explanation line in front of it.

**What they now check:**
- the model's line is present and is not listed in `added_lines`;
- no answer line, the added ones included, appears in the telemetry record.

The budget, usage and metrics assertions are unchanged. No product code was changed beyond the conflict resolution.

## 3. Verification (content: the merged tree, run before the commit and frozen as `65c6cfa`)

| Lane | Status | Count / result | Reason |
|---|---|---|---|
| `git diff --check` (staged), conflict-marker scan | EXECUTED | clean | Tier 1 |
| `check_secrets.py` (hardened) | EXECUTED | pass | Tier 1 |
| `check_project_state`, `check_architecture`, `check_tooling_config`, `check_policy_authority`, `check_external_provider_readiness` | EXECUTED | all pass | Tier 1 |
| `ruff check`, `ruff format --check` (apps/assistant) | EXECUTED | pass, 94 files | Tier 1 |
| `mypy ai_assistant assistant_eval` | EXECUTED | no issues, 41 files | Tier 1 |
| `evaluate_answers.py check` | EXECUTED | current: 84 turns, `1421eedb7fd536ea` (main's fixtures; nothing regenerated) | Tier 1 / section 7 |
| Focused assistant tests: A2 (`test_model_factory`, `test_default_request_golden`, `test_openrouter_adapter`, `test_budget_guard`, `test_budget_ledger`, `test_budget_cli`, `test_telemetry`) and #113/#114 (`test_answer_records`, `test_explanations`, `test_guardrails_dropped`, `test_grounding`, `test_knowledge_answers`, `test_required_p2`, `test_ai_assistant`, `test_streaming_resources`, `test_warm_up_security`, `test_speed`) | EXECUTED | 1,082 tests: 1,080 passed, 2 failed (the section 2 tests). After the fix, those two files pass 122/122 | Tier 2. Includes every assistant test file that main changed |
| Default-behaviour differential vs **new** main (parity probe: 336 cases, 41 model requests, `git archive 06e6a9b`) | EXECUTED | byte-identical, `7adc179fe8ef24d3a420f1e4a7819da5236ecbe46cc43f53f3030b48f10c6864` on both | Default profile unchanged relative to new main |
| Backend `test_ai_assistant_main_integration.py` | EXECUTED | 2/2 passed | Tier 2 |
| Frontend (`AiAssistantPanel.test.tsx` and others) | N/A | none of `apps/frontend` or `apps/backend` differs from `06e6a9b` | The merged frontend is main's content exactly; A2 changes no frontend file |
| Full assistant suite (about 1,900 tests) | NOT_EXECUTED | n/a | Tier 3. Every main-changed test file and every A2 test file ran in Tier 2. The remaining files are byte-identical on both sides. The last full run (`e0d45d4`) showed only Errno 24 failures known from base. Left to the reviewer to require |
| Full backend (3,173) and frontend (1,109) suites | NOT_EXECUTED (prior evidence covers code that is unchanged) | n/a | No backend or frontend file differs from main |
| E2E (`run_e2e.py`), physical Mongo | NOT_EXECUTED | n/a | Docker and Tesseract are unavailable. This is not newly invalidated: A2 changes nothing on the E2E path, which is main's content |
| Hosted CI | NOT_EXECUTED | n/a | Not pushed yet; earlier runs were billing-blocked |

## 4. Security and regression gates (implementer evidence; for independent confirmation)

- **Dormant locks L1–L4, S1–S3 and the empty shipped registry:** the A2 files (`model_factory.py`, `model_profiles.py`, `openrouter.py`, `budget.py`, `config.py`, `llm.py`, `telemetry.py`, `conftest.py`) are byte-identical to the reviewed `e0d45d4`. Their tests pass (Tier 2).
- **Default local model:** behaves exactly as on new main (parity probe).
- **PR #114 behaviour:** explanations, required lines and the exact-line guard tests pass. `guardrails.py`, `prompts.py`, `guide.py` and `briefing.py` are main's content unchanged.
- **Answer records and feedback:** `answer_records.py` is main's content; its tests pass.
- **No schema change** beyond A2's reviewed optional SQLite ledger.
- **R2-1 (Low):** still open; it is a Phase B prerequisite and does not block this merge.

## 5. Governance

- **Decisions:** D-090 / Amendment 2 (PR #114) and D-091 / Amendment 3 (A2) are distinct entries. Both still read PROPOSED in the repository.
- **For the owner:** the owner says D-091 X1–X9 and Amendment 3 were approved, with CI and E2E exceptions recorded on PR #116. Updating the decision status text is not part of this integration and was not done.
