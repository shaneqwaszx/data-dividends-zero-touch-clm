# D-100 AI Model Console Phases 2 to 4: Independent Re-Quality Gate (F-1/F-2 remediation and F-5 browser check)

Reviewer: independent QG (I did not author this content). Review only. No worktree edits, commits or `.env` access. The only things I wrote were reviewer probe scripts and screenshots in the scratchpad.
Date: 2026-10-29

## Reviewed identity

- Worktree: `C:\Users\shane\Desktop\claude-worktrees\d100-ai-console-phases-2-4-20261029`, branch `feat/d100-ai-console-phases-2-4`
- HEAD `a7e8e314e000cff98975147fd165caee8cc2edac`, tree `611d1d6b68c3839a25bc06774de6d16d57eb54f5`, parent `3b308c1` (earlier gate: PASS). Worktree clean.
- Delta reviewed: `git diff 3b308c1..a7e8e31`, 4 files, +12/-11 (`AiModelManagement.tsx`, `AiModelManagement.test.tsx`, `docs/PROJECT_STATE.md`, `docs/integration/AI_MODEL_CONFIGURATION.md`). Nothing else changed.

## Checks run (this session)

| Check | Result |
|---|---|
| HEAD, tree, parent and clean status | Match the candidate |
| `git diff --check 3b308c1..a7e8e31` | Clean |
| `npx vitest run src/pages/AiModelManagement.test.tsx` | 86/86 passed |
| `npx tsc -b --pretty false` | exit 0 |
| Implementer's MOCK harness `browser\run.cjs` (inspected first, then rerun by me as label `qg-reqg`) | 74/74 passed |
| Vite on 127.0.0.1:5181 serves this worktree's content | Yes: the served `AiModelManagement.tsx` contains the new F-1 text |
| My own probes (`browser\qg-measure.cjs`, `qg-row.cjs`, `qg-clip.cjs`; all `/api/**` mocked, writes refused) | Found R-1 below |

Harness inspection: it mocks every `/api/**` request from synthetic fixtures and refuses and records every non-GET request (0 writes recorded). The fixtures hold no real secrets; the only token-like value is `csrf_token: "mock-csrf"`. Its overflow check is document-level only (`scrollWidth - innerWidth`). Content clipped inside a `contain: paint` container is not caught by that check, which is how R-1 got past it.

## F-1 and F-2 verification against the backend

- **F-1: fixed and accurate.** The text now reads "(the most this page asks for; older events are not loaded)". The page requests `?limit=100`; `get_audit` accepts `le=500`. The test assertion was changed to the corrected string with the same strength (exact `toContain` of the full sentence).
- **F-2: fixed and accurate.**
  - The card is renamed "Server-configured models". It now says IT sets the environment baseline in the server environment (`baseline_entry`, `source="environment"`).
  - It says file profiles must use a loopback endpoint and any other is listed as not available. This matches `_file_entry`, which returns `unavailable` / `NOT_LOOPBACK`.
  - "Neither has a key managed on this page or a spending ledger" is accurate: there is no HR key form for them and `paid_estimate` returns `None` for non-`code` sources.
  - The troubleshooting text and the operator duties were updated to match.
  - The test now asserts the new subtitle plus one additional new sentence. It was replaced, not weakened.
- **Spending intro ("server-configured models have no spending ledger here"): accurate.** No ledger or spending view exists for `environment` or `file` sources. "Here" correctly scopes the claim.
- **Docs:** both docs edits only rename "local models" to "server-configured models".

## F-5 browser verification (MOCK only)

- **1440px:** all five sections show no clipped text and no overflow (my clip scan finds 0 elements).
- **Dialog behaviour, keyboard and contrast:** the harness checks pass at both widths. Covered: D3 inert and scroll lock, Tab trap, Escape focus restore, the paid confirmation for the first Claude run, five focusable nav links with a 2px outline, and WCAG AA text contrast per section.
- **360px:** Providers, Spending and Qualifications are fine.
- **360px Audit History: defect, R-1 below.**

## Findings

| ID | Severity | File:line | Finding | Required / recommended |
|---|---|---|---|---|
| R-1 | Minor (required) | `apps/frontend/src/pages/aiModels/aiModelConsole.css:326-335` (mobile block), with `design-system.css:409-410` | At ≤640px the audit table is restyled as cards, but the app-wide `.table-scroll > .table { min-width: 720px }` still applies, and the mobile override sets the wrapper to `overflow: visible`. The wrapper keeps `contain: inline-size paint`, so the content is clipped rather than scrolled. Measured at 360px: each row card is 720px wide (x 31–751) and the visible area ends at x=329. Text wider than about 285px is cut off with no way to scroll to it, and each card's right border is missing. Example: the Code meaning "The last Anthropic workspace and model check failed. Run Test connection." renders as "The last Anthropic workspace and model chec" (screenshot `scratchpad\qg\row-360-code.png`). The raw code stays visible, but this breaks the assigned 360px readability criterion. The defect was already present at `3b308c1`; my earlier gate did not browser-verify it (F-5) and the harness missed it. | **Required:** in the mobile block, give `.console-audit__table` `min-width: 0` (for example `.model-console .console-audit .table-scroll > .table { min-width: 0; }`). Add an element-level clipping check for the audit cards at 360px. |
| R-2 | Info | `AiModelManagement.tsx` escalation summary `<pre>` | At 360px, one Qualifications text node (the open escalation-summary `<pre>`) extends past the main column. This is pre-existing Phase 1 content and not introduced by this delta. | Note; optional `white-space: pre-wrap`. |
| R-3 | Info | `browser\run.cjs:46` | The harness's overflow check is document-level only, so it cannot detect clipping inside `contain: paint` or `overflow: hidden` containers. A 74/74 result therefore does not establish the mobile audit-card claim. | Recommended: add per-element clipping assertions. |
| R-4 | Info | harness fixture | The top bar shows "undefined Sandbox" because the mock `execution-profile` response does not match the app's field names. This is a harness artefact, not a product issue. | Note |

The earlier F-1 and F-2 findings are closed. F-3 and F-4 are unchanged (Info). F-5 is now verified for 1440px and for 360px apart from R-1.

## Change classification (delta)

Text and test-string changes only. API/type, schema, connector, configuration, business rule, mapping, auth/security, architecture, provider status and runtime behavior are unchanged. No backend file changed. The qualification basis is unaffected because no assistant file changed; it was verified as `33f60265…7e513` in the earlier gate.

## Verdict

**PASS WITH MINOR FIXES**

The F-1 and F-2 remediation is accurate and correctly tested, and nothing else changed. One required fix remains:

- **R-1:** the mobile (≤640px) audit cards are clipped by the inherited 720px table minimum width under `contain: paint`. The fix is bounded and CSS-only: `min-width: 0` for the audit table in the mobile block, plus an element-level 360px clipping check.

A focused re-review of the CSS delta and a rerun of the 360px audit browser check are needed after the fix. No other evidence is invalidated by a CSS-only change.
