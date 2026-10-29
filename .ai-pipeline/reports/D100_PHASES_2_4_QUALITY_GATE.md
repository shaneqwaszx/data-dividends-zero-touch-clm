# D-100 AI Model Console Phases 2 to 4: Independent Quality Gate

Reviewer: independent QG (I did not author or remediate this content). Review only; nothing in the worktree was edited, staged or committed.
Date: 2026-10-29

## Reviewed identity

- Worktree: `C:\Users\shane\Desktop\claude-worktrees\d100-ai-console-phases-2-4-20261029`, branch `feat/d100-ai-console-phases-2-4`
- HEAD `3b308c19094805cbabbc0050f46842ca0729bef8`, tree `19f71d6c0b22e0cb7646d005b94ecc5675687c60` (matches the candidate); worktree clean (`git status --porcelain` empty)
- Base `origin/main` = `90115e4ca6f4fbf4996e90d159521afe9ab7afdb`
- Commits: `b0a9d0e` (Phase 2), `337d87c` (Phase 3), `3b308c1` (Phase 4 and docs)
- Reviewed diff `git diff 90115e4..3b308c1`: 8 files, +1078/-80. `aiAssistant.ts`, `AiModelManagement.tsx`, `AiModelManagement.test.tsx`, `aiModels/ConsoleShell.tsx`, `aiModels/aiModelConsole.css`, `docs/PROJECT_STATE.md`, `docs/decisions/DECISION_LOG.md`, `docs/integration/AI_MODEL_CONFIGURATION.md`. No untracked task files.

## Checks run (this session)

| Check | Result |
|---|---|
| `git rev-parse HEAD` / tree / clean status | Matches the candidate; clean |
| `git diff --check 90115e4..3b308c1` | Clean (exit 0) |
| Backend/assistant/scripts untouched (`git diff --name-only ... -- apps/assistant apps/backend scripts`) | Empty: no backend change |
| `npx vitest run src/pages/AiModelManagement.test.tsx` | 86/86 passed |
| `npx vitest run` (full frontend) | 66 files, 1204/1204 passed |
| `npx tsc -b --pretty false` | exit 0 |
| Qualification basis (import path confirmed as the worktree's `apps/assistant/ai_assistant/model_qualification.py`) | `33f602653de73f372a787a9d4403daedcd589140aae02b86a4796cd994e87513`: unchanged |
| Test weakening | The only removed line in the test file is one type-import line, which the diff replaces. No assertion was removed or loosened. There are 26 new tests in 4 `describe` blocks (providers/spending, recovery, audit, dialogs/badges). |
| Browser (Playwright, mocked) | Not executed. The dev server on 5181 was reachable, but driving the authenticated shell with every `/api/**` mocked was not set up. The 360px/1440px layout claims rest on CSS inspection and jsdom only, so they are not browser-verified here. |

## Ground-truth verification of new user-visible claims

All checked against `model_admin.py`, `model_catalog.py`, `anthropic_runtime.py`, `anthropic_profiles.py` and `model_admin_store.py` at this HEAD:

- **No Claude key status, usage, headroom or reconciliation time sent: accurate.** `overview()` sends `budget` (OpenRouter `budget_view()`) only. For Claude it sends only `paid_estimate()` = {calls, reservation, estimate, effective_remaining, refusal, sufficient}. `anthropic_runtime.budget_status` is not projected otherwise.
- **"Not reported: this configuration is not available": accurate.** `paid_estimate` returns `None` when `source != "code"` or `status != "selectable"`.
- **A key problem appears among the server's codes: accurate.** In `budget_status` the `key_code` (`CREDENTIAL_MISSING` / `CREDENTIAL_INVALID` / `CREDENTIAL_ADMIN_REFUSED`) is the first refusal checked. `RECONCILIATION_STALE` is a real refusal.
- **Claude limits "at most US$5.00 lifetime, US$1.00 a day, 20 calls an activation": accurate as ceilings.** These are `LIFETIME_CEILING_MICRO_USD`, `DAILY_CEILING_MICRO_USD` and `MAX_CALLS_CEILING`. "Reconciliation within 24 hours" matches the `paid_estimate` / start comments. `AI_ASSISTANT_ANTHROPIC_API_KEY` is `CREDENTIAL_VARIABLE`.
- **Claude Balanced and Fast are one provider: accurate.** Both are `_claude_entries` from one `anthropic_profiles` set, sharing a ledger and key.
- **providerKind (`anthropic`; `source=="code"` -> OpenRouter; otherwise local): correct for the code entries.** That covers `openrouter` and dormant `remote`, both GPT-OSS. The environment baseline is also placed under "Local models"; see F-2.
- **Audit: partly accurate.** The page requests `limit=100`; the server's `get_audit` accepts `le=500` and `store.events(limit)`. "Most recent 100" in the docs is accurate. The UI sentence "the most it sends at once" is not (F-1).
- **GPT-OSS duties ("raising the daily limit needs confirmation", "a lifetime raise needs confirmation and a ledger that reconciles"): consistent with the code.** The D-098 refusal codes `DAILY_CONFIRMATION_REQUIRED`, `CAP_CONFIRMATION_REQUIRED` and `CAP_RAISE_CHECKS` support them.
- **No new request: confirmed.** Providers and Spending read from the existing overview, and a test asserts no extra request. Audit filtering is client-side and a test asserts no request. `fetchModelAudit` is unchanged apart from extracting the constant (same URL `?limit=100`).

## Cross-phase invariants

- **Paid run still requires the confirmation.** `runQualification` routes `isPaidRemote` (openrouter or anthropic) to `setPaidConfirm`. `startPaid` sends only the server's `calls`. The new "Run first qualification…" button uses the same path, and a test covers Claude (I-1).
- **Backend authority unchanged.** The first-run button is shown only when `usable && configured && endpoint`; the server still refuses.
- **No HR-editable Anthropic limits, no HR Anthropic key entry, and no new spending authority.** `ClaudeSpending` is read-only, and tests assert no Claude inputs or key form.
- **Separate ledgers and no automatic fallback.** The GPT-OSS controls are unchanged, and Claude is never linked to them (M-2 fix plus test).
- **Unchanged:** synthetic boundary, routing, thresholds, G-8, activation policy, eligibility and basis. No backend diff, and the basis hash is verified.
- **RBAC/capability:** no change to routes or guards.

## Findings

| ID | Severity | File:line | Finding | Required / recommended |
|---|---|---|---|---|
| F-1 | Minor | `apps/frontend/src/pages/AiModelManagement.tsx:1333` | When 100 events are loaded, the audit scope note says "(the most it sends at once; older events are not loaded)". The server accepts up to 500 (`get_audit` `le=500`); 100 is the most this page asks for. The "older events are not loaded" part and the client-side-only statement are correct, so no hidden search is implied, but the server claim is inaccurate. | Recommended: reword to "the most this page asks for". |
| F-2 | Minor | `apps/frontend/src/pages/AiModelManagement.tsx:843` (with `providerKind` at ~253) | The environment baseline (`source "environment"`, `deployment "openai_compatible"`) is listed under "Local models". That card states they "run on this server's loopback address, so they need no key". The baseline's URL comes from `AI_ASSISTANT_LLM_BASE_URL` (default loopback, but not enforced for the baseline's chat use) and it may carry `llm_api_key`. File profiles are enforced to loopback; the baseline is not. In the default configuration this is presentation-accurate. | Recommended: qualify the sentence (for example, "Local profiles from the model profiles file run on a loopback address…") or describe the baseline as set by the environment. |
| F-3 | Info | `apps/frontend/src/pages/aiModels/ConsoleShell.tsx:105-121` | `isolate()` makes inert only the siblings that exist when the dialog opens. A banner that React mounts outside the dialog while it is open is not inert. It is low impact: such banners appear after an action, when the dialog is closed. | Note only. |
| F-4 | Info | `apps/frontend/src/pages/aiModels/aiModelConsole.css:188` | `.model-console form` now applies flex layout to every console form, including Phase 1's Spending and key forms. This is a presentation-only change; tests pass, but it is not browser-verified in this gate. | Note only; confirm visually during owner review. |
| F-5 | Info | n/a | 360px and 1440px layout, contrast "4.5:1" and the mobile audit card layout are not browser-verified by this gate (mock browser run not executed). | Note; the dependent claim is unverified here, not failed. |

There are no Blocker or Major findings.

## Status of prior findings and debt

- **M-1: closed.** `readable()` now gets the deployment for the Recovery `run.code`, the `QualificationDetail` code and connection-test codes. The start-up/unavailable `reverted` code and audit rows whose provider is unknown use the provider-neutral `ANY_PROVIDER` wording. Audit rows with a known configuration use that configuration's deployment. Tests are named "(M-1)".
- **M-2: closed.** The paid dialog's insufficient-room banner gives Claude-specific guidance. The Recovery "Review spending controls" link reads "View Claude's limits (read-only)" for Claude, and `ESCALATE_KEY_OWNER` uses the Claude wording. Tested.
- **I-1: closed.** `recoverable` now includes both paid deployments (`isPaidRemote`), so unqualified Claude configurations appear. Their first run goes only through the paid confirmation. Tested.
- **D2: open (not in the assigned Phase 4 debt scope).** Recovery cards now show the provider label, but RemoteDetails for non-active remote configurations is unchanged.
- **D3: closed.** The background is inert and scroll is locked while a dialog is open. Tested.
- **D4: closed by earlier work.** `DECISION_LOG.md` has "D-100 … Phase 1 (PROPOSED)", and this diff adds a Phase 2 to 4 update.
- **D5: closed.** The guard implements the recommended check (restore only if focus is on body or null, disconnected, or inside the closed dialog). Tested.
- **D6: closed.** Key, spending and running badge variants are unit-tested.

## Change classification

- API/type: no API change. One new exported frontend constant (`MODEL_AUDIT_LIMIT`, the same value 100) and the frontend-only export `ANY_PROVIDER`. No shared type changes.
- Schema: no change.
- Connector: no change.
- Configuration: no change.
- Business rule: no change. Thresholds, G-8, activation, eligibility, ledger, routing and limits are untouched.
- Mapping: no change.
- Auth/security: no change. There is no new RBAC or capability path, no key entry and no secret exposure. The new raw codes shown are closed server codes.
- Architecture: no change. This is frontend presentation within existing components.
- Provider status: no change. Claude remains D-099 PROPOSED, and nothing is claimed Live.
- Runtime behavior: frontend presentation only. One new user-reachable control ("Run first qualification" for unqualified external configurations) goes through the existing paid confirmation and backend authorization. Backend runtime is unchanged.

## Verdict

**PASS**

All assigned Phase 2 to 4 criteria are verified against the backend code. Invariants are preserved, the basis is unchanged, no backend file changed, tests were added without weakening, and the full frontend suite and typecheck pass. F-1 and F-2 are minor wording-accuracy recommendations, not required for this gate. If the owner chooses to fix them before publication, the changed text needs a fresh focused review. Browser and visual claims (F-5) are not verified by this gate.

Readiness: ready for owner review and publication authorisation (pre-PR check still to be run on the clean committed state). Not Live; no paid call was made by this review.
