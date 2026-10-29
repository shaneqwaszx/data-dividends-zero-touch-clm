# D-099-FU2 Quality Gate — Claude-specific `PROVIDER_LIMIT_NOT_CHECKED` guidance

An independent focused reviewer (a fresh agent, not the implementer) ran this gate on
2026-10-29. Subagents cannot write files, so the coordinator saved the report; its substance is
as the reviewer returned it.

**Verdict: PASS.** No fix is required. One low-severity test-coverage advisory is noted; it does
not block.

## Frozen identity

- Worktree: `C:\Users\shane\Desktop\claude-worktrees\assistant-claude-sonnet-console-20261029`
- Branch: `feat/assistant-claude-sonnet-console` (draft PR #130); published head `32263b9`
- Reviewed commit: `c3a5d4939b62b7e94234447d4926a0754b8c3fcf`, tree
  `9af227088bf5b668f43fee3f3b98cfbfc1cce57f`. HEAD and the clean working tree were the same at
  the start and the end.
- Delta `32263b9..c3a5d49`: 5 files, +145/−1.

| File | Change |
| --- | --- |
| `model_admin.py` | +14/−1 |
| `test_claude_runtime.py` | +50 |
| `aiAssistant.ts` | +1 |
| `AiModelManagement.test.tsx` | +8 |
| FU2 implementation report | +73 |

- `git diff --check` is clean, and the new Markdown has no trailing whitespace.

## Verification

### 1. Scope of the `refuse_start` change

`model_admin.py:1502-1519`:

- The audit call is untouched.
- The function now returns `_refusal(status, code, message)`.
- `message` is the Anthropic key only when `code == "PROVIDER_LIMIT_NOT_CHECKED"` **and**
  `entry.deployment == "anthropic"`; otherwise it is `None`.
- `_refusal` uses `message_code or code` only to look up the message. The response code and the
  HTTP status are unchanged.
- Every other caller is unaffected: `:1531`, `:1539`, `:1545`, `:1553`, `:1557` and `:1558`. The
  direct `_refusal(409, "PROVIDER_CHECK_FAILED")` at `:2032` bypasses `refuse_start`.
- The gating order is unchanged.
- In `MESSAGES`, one key was added; none was removed or changed.

### 2. Accuracy of the new message

- The text matches `anthropic_runtime.check_workspace` (`:374-408`). That check is a free,
  content-free `GET /v1/models/{MODEL_ID}` that confirms the models endpoint is reachable, the
  workspace header matches, and the model is available.
- `budget_status` (`:557-559`) emits `PROVIDER_LIMIT_NOT_CHECKED` or `PROVIDER_CHECK_FAILED`.
  `model_admin.py:1554-1555` folds both into the first code, and "Run Test connection first" is
  correct guidance for both.
- `PROVIDER_KEY_LIMIT_EXHAUSTED` is confirmed unreachable for Claude:
  - only `remote_test.py:592` emits `PROVIDER_LIMIT_EXHAUSTED`, on the OpenRouter path;
  - Claude's `key_code` can only be `CREDENTIAL_MISSING`, `CREDENTIAL_INVALID` or
    `CREDENTIAL_ADMIN_REFUSED`.

### 3. Frontend safe list

- The entry is necessary. `aiAssistant.ts:95-96` shows only server messages that are listed and
  at most 256 characters, and the parity test fails without the entry (mutation M6).
- The entry is safe: a fixed literal of 112 characters, identical to the server string.
- The new vitest case covers the page's display path.

### 4. Tests catch regressions

The mutations ran in a throwaway `git archive` copy, deleted afterwards.

| Mutation | Result |
| --- | --- |
| M1: drop the `deployment == "anthropic"` condition | caught (GPT-OSS byte-for-byte test) |
| M2: drop the `code == "PROVIDER_LIMIT_NOT_CHECKED"` condition | **survived** — see L-1 |
| M3: revert the Claude message | caught |
| M4: return the message key as the public code | caught |
| M5: remove the refusal audit call | caught |
| M6: remove the safe-list entry | caught (parity test) |

Two failures in the M2 combined run were artefacts of the temp copy, not of M2:

- leftover M6 residue in that copy;
- the boundary-file test, which needs `apps/backend` and passes in the real worktree.

### 5. GPT-OSS message

`MESSAGES["PROVIDER_LIMIT_NOT_CHECKED"]` is byte-identical to `32263b9` (programmatic equality),
and the new test asserts the exact string.

### 6. Boundary and basis

- `build_synthetic_boundary.py --check` reports current.
- `qualification_basis()` is still
  `33f602653de73f372a787a9d4403daedcd589140aae02b86a4796cd994e87513`.
- Neither changed source file is in `BASIS_FILES`.

## Commands

| Command | Result |
| --- | --- |
| pytest `test_claude_runtime`, `test_d098_recovery`, `test_model_management`, `test_claude_console`, `test_remote_test`, `test_spending_controls` | 345 passed (196 s), no `Errno 24` |
| pytest `test_claude_runtime.py -k unchecked` | 2 passed |
| browser safe-list parity test | 1 passed |
| `ruff check .` / `ruff format --check .` | clean / 129 files formatted |
| `mypy ai_assistant assistant_eval` | no issues (56 files) |
| `npx vitest run` | 66 files, 1,160 passed |
| `npx tsc -b --pretty false` | exit 0 |

## Findings

- **Critical / High / Medium:** none.
- **L-1 (Low, advisory, test coverage)** — `test_claude_runtime.py:874-921`:
  - No test pins that a Claude refusal with a different code keeps that code's own message, for
    example `PAID_CONFIRMATION_REQUIRED` or `QUALIFICATION_BILLING_UNRECONCILED`.
  - So M2 would quietly re-word unrelated Claude refusals.
  - The production code is correct; only the guard against a future regression is missing.
    Hardening it is optional, later.
- **Observation (pre-existing, out of FU2 scope):** `MESSAGES["PROVIDER_CHECK_FAILED"]` ("The
  OpenRouter key could not be checked") is raised only by `require_provider_limit` (`:2032`) on
  the OpenRouter D-098 budget endpoints.

## Required fixes

None.

## Readiness

The reviewed content (`c3a5d49`, tree `9af22708…`) is ready for the coordinator's publication
step, under the owner's existing approval and provided the content stays unchanged.

No paid run, no provider network call, no Mongo access and no `.env` access took place.

## Git status

- The worktree was clean before and after the gate, with HEAD unchanged.
- The reviewer made no edits, staging, commits or branch changes in the repository.
