# D-099 + D-100 Phase 1 integration candidate (implementation report)

Date: 2026-10-29. Disposable worktree
`C:\Users\shane\Desktop\claude-worktrees\d099-d100-integration-20261029`, local branch
`integration/d099-d100-phase1-20261029` (no upstream, not pushed, not a PR). Offline only: no
paid Anthropic or OpenRouter request, qualification, activation or deployment.

## Composition

| Step | Commit |
| --- | --- |
| base: latest `origin/main` (fetched 2026-10-29) | `8c7ea99` |
| merge D-099 `feat/assistant-claude-sonnet-console` at `32263b9` (PR #130 `e63ff311` + FU1 `b7a5ca6` + FU1 QG report) | `bfb8c90` |
| merge D-100 `feat/d100-ai-console-phase1` at `45ae602` (PR #131) | `9b97737` |
| narrow compatibility fixes + docs (this report) | see the commit after `9b97737` |

Both merges were textually clean (no conflicts). Neither existing PR worktree was edited. The
assistant service in the candidate is byte-identical to the reviewed D-099-FU1 content
(`git diff 32263b9 HEAD -- apps/assistant scripts tests` is empty); `ConsoleShell.tsx` and
`aiModelConsole.css` are identical to D-100's.

## Narrow D-100 compatibility fixes (`AiModelManagement.tsx` only)

D-100 treated `openrouter` as the only external, paid deployment. With D-099, Claude
(`anthropic`) is a second one:

1. **Paid-run confirmation for Claude.** *Run qualification…* on a Claude configuration now
   opens the existing paid-run dialog instead of starting directly. The backend already
   requires `confirm_paid_calls` for every `code` profile (`model_admin.post_qualification`),
   so without this a Claude qualification from the console would be refused with
   `PAID_CONFIRMATION_REQUIRED` (fail-closed but unusable). The dialog's wording names the
   Anthropic API and Claude's separate ledger, says the GPT-OSS limits do not apply, and
   repeats the 24-hour reconciliation rule; the GPT-OSS wording is unchanged.
2. **Activation warning** for Claude (external, paid API; synthetic cases only; its own
   ledger, daily allowance, call limit and workspace limit; no automatic switch).
3. **Inspector**: Claude's notice (its fixed safeguards; GPT-OSS controls never apply), and the
   existing `RemoteDetails` line (provider, reasoning, thinking, scope) for any remote
   configuration (D-100 debt D2 addressed for the inspector).
4. **Refusal codes**: the Option B readiness and spending codes are named
   (`ANTHROPIC_ATTESTATION_MISSING`, `ANTHROPIC_SETTINGS_INVALID`, `WORKSPACE_NOT_ATTESTED`,
   `WORKSPACE_LIMIT_NOT_ATTESTED`, `LEDGER_PATH_SHARED`, `LEDGER_PROFILE_MISMATCH`,
   `LIFETIME_CEILING_EXCEEDED`, `RECONCILIATION_STALE`, `CREDENTIAL_ADMIN_REFUSED`); shared
   codes whose wording names OpenRouter (`PROVIDER_LIMIT_NOT_CHECKED`, `PROVIDER_CHECK_FAILED`,
   `CREDENTIAL_*`, `LEDGER_UNAVAILABLE`, `DAILY_ALLOWANCE_EXHAUSTED`,
   `LIFETIME_CAP_EXHAUSTED`) get Claude wording when the profile is Claude
   (`readable(code, deployment)`); without a deployment the text is unchanged.
5. **Spending**: Spending & Limits says its controls apply to GPT-OSS only and states
   Claude's fixed safeguards; the overview's *Available now* / *Calls this activation* figures
   are labelled *(GPT-OSS)* when Claude is listed.

Not changed: backend, API, types, spending controls, keys, RBAC, routes/navigation, console
shell, dialogs' focus/escape behaviour, CSS, the stale-but-unemitted
`ANTHROPIC_PROVIDER_CONTROLS_MISSING` text (kept; D-099's own test asserts it). No Phase 2.

## Docs

- `DECISION_LOG.md`: **D-100** entry appended after D-099 (D-100 had none: its debt D4); D-099
  entries untouched. Note: D-101 is taken on the unrelated GoldTier branch
  `feat/goldtier-group-company-name-shell-20261029`, which also appends at the end of the file
  — a textual conflict to resolve when that lands, no number clash.
- `AI_MODEL_CONFIGURATION.md`: "Claude in the console" paragraph after D-100's.
- `PROJECT_STATE.md`: D-100 + integration-candidate section.

## Evidence (on the candidate content)

| Check | Result |
| --- | --- |
| Frontend `vitest run` | 66 files, 1,176 tests passed (52 → 59 in `AiModelManagement.test.tsx`; 7 new Claude-console tests) |
| `tsc -b` | clean |
| `npm run build` | built (existing chunk-size warning only) |
| Browser (MOCK: Vite dev server, StrictMode, scripted Chromium DPR 1, every `/api/**` mocked, writes never answered) at 1440×900 and 360×740 | 30/30 checks passed: no horizontal overflow (overview, dialog, spending), Claude family + provider, inspector provider/reasoning/thinking + safeguards, Claude paid dialog wording with focus inside, Fast refusal in Anthropic terms with Start disabled, GPT-OSS dialog unchanged, Claude Activate blocked until qualified, Spending note, no write sent, no page error |
| Assistant suite in the candidate (`PYTHONPATH` pinned to this worktree) | 2,842 collected, 2,828 passed, 14 failed — all 14 `OSError: [Errno 24] Too many open files` (Windows handle exhaustion in real-socket tests); `test_model_factory`, `test_phase_b_live`, `test_required_p2`, `test_streaming_resources` rerun in isolation: 289 passed |
| MOCK end-to-end multi-turn journey | `tests/test_claude_multi_turn.py::test_an_rm_conversation_on_the_activated_claude_model_is_answered`: HR connection test → paid qualification (mock Anthropic) → activation → RM asks 3 turns through the real streaming route with the browser's history shape; 3/3 answered by Claude, request turns 1/3/5, no OpenRouter or baseline call, every ledger call verified. **MOCK** |
| Root `tests/test_check_secrets.py`, `test_claude_skill_pointers.py` | 40 passed |
| `scripts/check_secrets.py` | passed |
| Qualification basis | `33f602653de73f372a787a9d4403daedcd589140aae02b86a4796cd994e87513` (same as D-099-FU1) |

Screenshots and the browser script are in the session scratchpad (not tracked).

## Change statement

API/type: no. Schema: no. Connector: no (beyond D-099). Configuration: no. Business rule: no.
Mapping: no. Auth/security: no change; paid-run confirmation now also covers Claude in the UI
(the server already required it). Architecture: no. Provider status: unchanged (Claude
Mock/offline; GPT-OSS unchanged). Runtime behaviour: console presentation only.
