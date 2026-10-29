# D-099-FU2 — Claude-specific `PROVIDER_LIMIT_NOT_CHECKED` guidance (implementation report)

Date: 2026-10-29. Branch `feat/assistant-claude-sonnet-console` (draft PR #130).
Base: published head `32263b9`. This is offline work only: no paid call, no qualification and
no activation.

## Problem

`POST /admin/models/{profile_id}/qualifications` refuses a paid start before the provider
check has passed in this process, returning the code `PROVIDER_LIMIT_NOT_CHECKED`. The message
said: "Run Test connection first so the OpenRouter key's own limit is checked." That is wrong
for Claude. Claude's free check reads the attested Anthropic workspace and the model, and it
has no readable key limit.

This is the only OpenRouter-worded server refusal that a Claude configuration can reach:

- `PROVIDER_KEY_LIMIT_EXHAUSTED` needs `PROVIDER_LIMIT_EXHAUSTED`, which Claude's spending view
  never emits.
- The other OpenRouter-worded messages belong to OpenRouter-only endpoints.

## Change

| File | Change |
| --- | --- |
| `apps/assistant/ai_assistant/model_admin.py` | adds a `MESSAGES["PROVIDER_LIMIT_NOT_CHECKED_ANTHROPIC"]` entry; in `refuse_start`, an `anthropic` entry refused with `PROVIDER_LIMIT_NOT_CHECKED` gets that message |
| `apps/frontend/src/aiAssistant.ts` | adds the new fixed message to `SAFE_ERROR_MESSAGES`; the browser shows only listed server messages, and `test_every_model_management_message_is_in_the_browser_safe_list` requires the entry |
| `apps/assistant/tests/test_claude_runtime.py` | two tests (below) |
| `apps/frontend/src/pages/AiModelManagement.test.tsx` | one test: the page shows the new message as written |

The new message is: "Run Test connection first so the Anthropic workspace and model are
checked (a free model read). Nothing started."

These are unchanged:

- the public code `PROVIDER_LIMIT_NOT_CHECKED` and the HTTP status 409;
- the audit event (`QUALIFICATION_STARTED`, `refused`, with the same code);
- the gating order and every other refusal code;
- the GPT-OSS message, byte for byte;
- provider behaviour.

## Evidence

All of the following is offline/MOCK.

- **New tests** (`-k unchecked`): 2 passed.
  - **Claude:** the start before the check returns 409 with the code above and the Anthropic
    message, which does not mention "OpenRouter". One refused audit event carries that code.
    Nothing is running, and no Claude or OpenRouter request is made. After the free connection
    test passes, the same start returns 202.
  - **GPT-OSS:** the same refusal keeps the exact original message, with one refused audit
    event and no OpenRouter chat.
- **Focused suites** (`test_claude_runtime`, `test_claude_console`, `test_claude_multi_turn`,
  `test_model_management`, `test_d098_recovery`, `test_remote_test`, `test_spending_controls`):
  410 passed. The one failure was the safe-list parity test before the frontend entry was
  added. After the entry, `test_d098_recovery.py` passed 79/79.
- **Frontend:** `vitest run` passed 66 files, 1,160 tests; `tsc -b` is clean; `npm run build`
  built.
- **Static checks:** `ruff check` and `ruff format --check` are clean, and strict `mypy` on
  `ai_assistant` and `assistant_eval` is clean.
- **Boundary:** `build_synthetic_boundary.py --check` reports current, so there is no new
  vocabulary.
- **Qualification basis:** unchanged at
  `33f602653de73f372a787a9d4403daedcd589140aae02b86a4796cd994e87513`. Neither `model_admin.py`
  nor the frontend is in `BASIS_FILES`.

## Change statement

- API/type: no; the response `message` text differs for Claude only.
- Schema, connector, configuration, business rule and mapping: no.
- Auth/security: no; the browser safe list gains one fixed string.
- Architecture: no.
- Provider status: unchanged (Claude Mock/offline).
- Runtime behaviour: only the wording of one Claude refusal.
