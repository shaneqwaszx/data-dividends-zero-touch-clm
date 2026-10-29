# D-099 + D-100 Phase 1 integration — independent Quality Gate (round 1)

Independent reviewer (fresh agent, not the implementer), 2026-10-29; saved by the
coordinator (subagents cannot write files). Substance as returned.

## 1. Executive result

**PASS WITH MINOR FIXES.** Both merges are faithful. Each one equals git's own clean
`merge-tree` result tree-for-tree, and no hunk was lost. The assistant service is
byte-identical to `32263b9`. `ConsoleShell.tsx` and `aiModelConsole.css` equal `45ae602`. The
compatibility commit is narrow: no Phase 2, and no backend, API, type or CSS change.

Every path that starts a paid run, GPT-OSS or Claude, goes through the confirmation dialog.
GPT-OSS wording and behaviour are unchanged, and all required evidence passes.

What remains is a set of bounded wording faults: OpenRouter or GPT-OSS wording, or fixed
figures, where a Claude profile is in scope. None is a security or contract issue, and none
can start a paid run.

## Frozen identity

- Worktree: `C:\Users\shane\Desktop\claude-worktrees\d099-d100-integration-20261029`
- Branch: `integration/d099-d100-phase1-20261029`
- HEAD: `53f12eed97b7c6500d1127a82ac86e375fdbc7ce`
- Tree: `ad834450faf077c7df04debc7b6524527c7c0e94`
- Composition:
  - base `8c7ea99`
  - D-099 `32263b9`, merged as `bfb8c90`
  - D-100 `45ae602`, merged as `9b97737`
  - compatibility and docs commit `53f12ee`
- 44 files in `git diff 8c7ea99 53f12ee`. The compatibility delta is 6 files.

## 2. Acceptance checklist (all PASS)

- **Faithful merges:**
  - `git merge-tree --write-tree 8c7ea99 32263b9` equals the `bfb8c90` tree (`18897be8…`).
  - `git merge-tree bfb8c90 45ae602` equals the `9b97737` tree (`efb9cb1f…`).
  - In `AiModelManagement.tsx`, 480 of the 492 added lines are unchanged. The other 12 are
    exactly the lines the compatibility commit edits.
- **Unchanged inputs:** the assistant code equals `32263b9`, and the D-100-only files equal
  `45ae602`.
- **Console preserved:** shell, navigation, inspector, dialogs and accessibility. Focus moves
  inside the dialog, Escape closes it, and there is no overflow.
- **Understandable for Claude:** the Anthropic provider, reasoning, qualification states and
  refusal codes are understandable, with minor gaps (L-1 to L-4).
- **Narrow compatibility only, no GPT-OSS regression:** `readable(code)` is unchanged, and the
  GPT-OSS dialog is byte-identical.
- **No paid run without confirmation:**
  - `startModelQualification` has two call sites. `AiModelManagement.tsx:970` is local only
    (`!isPaidRemote`). `:978` is the dialog's `startPaid`.
  - The inspector `onQualify` and the Recovery `onRetry` both go through `runQualification`.
  - Start is disabled unless `sufficient`.
  - The server also refuses with `PAID_CONFIRMATION_REQUIRED` (`model_admin.py:1532-1533`).
- **Separate controls and docs:** spending controls stay separate and nothing switches models
  automatically. The docs are reconciled append-only.
- **PROJECT_STATE EOL:** `--stat` equals `--ignore-cr-at-eol` (18 insertions). The CR count
  stays at 724.

## 3. Contract and integration

There are no High or Medium findings. The reviewer checked the backend ceilings in
`anthropic_runtime.py:106-111` and `config.py:96-97`:

- lifetime: 5,000,000 µUSD;
- daily: 1,000,000 µUSD, configurable from 0 to 1,000,000;
- calls: 20 per activation, configurable from 1 to 20;
- reconciliation: within 24 h for paid runs, 7 days for chat.

The UI statement "Test connection is a free model read" is true. All Claude codes from
`readiness`, `budget_status` and `resolve_key` are named. Provider status is unchanged
(Mock/offline).

## 4. Tester and adversarial

| Command | Result |
| --- | --- |
| `npx vitest run` | 66 files, 1,176 passed |
| `npx tsc -b --pretty false` | exit 0 |
| `npm run build` | built; chunk-size warning only; `dist/` ignored |
| Assistant full suite (pinned `PYTHONPATH`) | 2,842 collected, 2,828 passed, 14 `Errno 24` |
| Isolated rerun of the four socket files | 289 passed |
| MOCK journey `test_an_rm_conversation_on_the_activated_claude_model_is_answered` | 1 passed |
| Root `test_check_secrets.py`, `test_claude_skill_pointers.py` | 40 passed |
| `check_secrets.py`, `check_architecture.py`, `check_project_state.py` | PASS |
| `git diff --check 8c7ea99 53f12ee` | clean |
| Browser (MOCK, own Vite server, DPR 1, `/api/**` mocked, writes aborted) at 1440×900 and 360×740 | 34/34 passed; 0 writes, 0 page errors; server stopped |

The MOCK journey proves the following:

- HR activates Claude Balanced against an in-memory Anthropic mock.
- An RM has a three-turn conversation through the real `/chat/stream` route, sending the
  browser's history shape.
- There are 3 Claude POSTs, 0 OpenRouter calls and 0 baseline calls.
- The message counts are 1, 3 and 5, with user and assistant roles only.
- Every ledger call is verified, and the key never appears in a response.

It does not prove real Anthropic interoperability. No paid call was made.

## 5. Code and architecture (all Low)

- **L-1** `AiModelManagement.tsx:221`: the Recovery card calls `readable(paid.refusal)`
  without `item.deployment`, so a Claude profile would show OpenRouter wording.
- **L-2** `:128-166`: the Recovery `CAUSE_TEXT` and `ACTION_TEXT` use OpenRouter wording for
  every provider. `model_admin.diagnose` applies them to Claude runs too. This predates the
  integration. The affected entries are:
  - `LEDGER_NOT_RECONCILED`, `SERVER_SETTINGS`, `CALLS_NOT_VERIFIED`, `PROVIDER_REFUSED`,
    `KEY_LIMIT_EXHAUSTED`;
  - the actions `ESCALATE_KEY_OWNER` and `ESCALATE_OPERATOR`.
- **L-3** `:1047`: the AI-unavailable banner names GPT-OSS, but a stored Claude activation can
  also become AI unavailable (D-099 C8 P-6). This predates the integration.
- **L-4** `:1108` and `:100`: US$1.00 a day and 20 calls are stated as fixed values, but they
  are defaults and ceilings. At `:88`, `LIFETIME_CEILING_EXCEEDED` omits the case where the
  cap is not above the opening usage.

Informational:

- **I-1:** the server refusal messages at `model_admin.py:215-221` name OpenRouter for Claude.
  This is D-099 backend wording, out of frontend scope; record it as a follow-up.
- **I-2:** `recoverable` lists Claude only once it has a qualification. This fails safe.
- **I-3:** the stale `ANTHROPIC_PROVIDER_CONTROLS_MISSING` text is kept on purpose, because
  D-099's own test asserts it.

## 6. Security

No findings:

- no secret appears in the UI changes;
- RBAC and the capability route are unchanged;
- the server still enforces paid confirmation;
- no provider network call was made, no `.env` was read and Mongo was not touched.

## 7. Required fixes

All are wording-only changes in `AiModelManagement.tsx`:

1. L-1: pass `item.deployment`.
2. L-2: give the Recovery texts Claude or neutral wording.
3. L-3: make the banner provider-neutral.
4. L-4: use "at most" wording, and widen the `LIFETIME_CEILING_EXCEEDED` text.

A recheck needs only that file, its test and a frontend rerun.

## 8. Readiness

- The candidate is ready for the bounded remediation, followed by a delta recheck.
- Publication is the owner's decision.
- No paid run, qualification or activation was authorised or made (US$0).
- Claude interoperability is unverified; the evidence is MOCK/offline only.
- Hosted CI was not checked.

## 9. Git status

- HEAD `53f12ee`, no upstream.
- `git status --short` was empty before and after the gate.
- The reviewer made no edit, commit, stash, reset, merge, push or branch switch.
- The reviewer's Vite server was stopped.
