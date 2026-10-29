# D-100 AI Model Console Phases 2 to 4: implementation and evidence

Date: 2026-10-29. Branch `feat/d100-ai-console-phases-2-4` (local only, not pushed), worktree
`claude-worktrees/d100-ai-console-phases-2-4-20261029`, base `origin/main` `90115e4`
(D-100 Phase 1 with D-099, PR #131 merged). Presentation only; no paid call, qualification or
activation was made.

## Commits

| Milestone | Commit | Tree |
|---|---|---|
| Phase 2 Providers and Spending & Limits | `b0a9d0e` | `54701cd` |
| Phase 3 Qualifications and Recovery | `337d87c` | `a61c8ee` |
| Phase 4 Audit History, polish and docs | `3b308c1` | `19f71d6` |
| QG F-1/F-2 wording remediation | `a7e8e31` | `611d1d6` |
| Re-QG R-1/R-2 CSS remediation (final code) | `d3aefc2` | `58e8743` |

## What changed

- **Phase 2.** Providers: one card per provider (OpenRouter; Anthropic API; server-configured
  models), each with its configurations' availability and last connection test, and who manages
  what (HR on the page, an operator on the server, the key or workspace owner at the provider).
  Claude Balanced and Fast are two configurations of one Anthropic provider. The OpenRouter key
  form is unchanged. For Claude the page states that the server does not send key status, usage,
  headroom or reconciliation time, and lists the server's codes with their raw values. Spending &
  Limits: the HR-editable GPT-OSS panel and a read-only Claude panel that shows only the server's
  `paid_qualification` figures; Claude's panel also appears when the OpenRouter test mode is off
  (previously the page said no paid limits applied); an unreadable GPT-OSS ledger reads
  "Unavailable" instead of a dash. Console forms are no longer centred by the app-wide form rule.
- **Phase 3.** Recovery cards show technical qualification, answer quality and availability
  apart, the server's raw codes, the latest run's gates and provider-specific troubleshooting.
  I-1: every external configuration is listed, including unqualified Claude; a first run uses the
  existing paid confirmation. M-1: run codes and results are worded for the configuration's
  provider; a provider-unknown code (start-up revert, audit row without a configuration) is worded
  without naming one. M-2: the paid dialog and recovery link never send Claude to the GPT-OSS
  spending controls.
- **Phase 4.** Audit History: readable rows with raw codes, machine-readable times,
  configuration names and revision; search and action/outcome filters over the loaded events
  only (`MODEL_AUDIT_LIMIT` = 100, shared with the request), stated on the page; loading, empty,
  no-match and error-with-retry states; labelled cards with table roles on narrow screens. Section
  introductions; console text at 4.5:1. D3 inert background and scroll lock; D5 focus-restore
  guard; D6 badge tests; menu badge wrap fixed.

No API, schema, connector, configuration, business rule, mapping, auth/security, architecture,
provider status, qualification threshold, G-8, eligibility, ledger, routing or backend runtime
change. Runtime behaviour changed in frontend presentation only (including the "Run first
qualification…" button, which goes through the existing paid confirmation and backend checks).

## Evidence (on the final candidate unless stated)

| Check | Result |
|---|---|
| Focused `AiModelManagement.test.tsx` | 86/86 (61 at base; 26 new; none removed or loosened) |
| Full frontend vitest | 66 files, 1,204/1,204 on `3b308c1` and again on `d3aefc2` |
| `tsc -b` / `npm run build` | exit 0 / built on `d3aefc2` (pre-existing chunk-size warning) |
| Assistant focused regression (12 files incl. `test_synthetic_eligibility`, `test_claude_*`, `test_model_management`, `test_budget_*`, `test_phase_b_*`) | 622 collected, all passed (exit 0) |
| Qualification basis from the worktree's own `apps/assistant` | `33f602653de73f372a787a9d4403daedcd589140aae02b86a4796cd994e87513`, unchanged |
| `scripts/check_secrets.py` | pass |
| `scripts/pre_pr_check.py` | PASS on `3b308c1`; rerun on the final committed state (with this report), recorded in the handoff |
| MOCK browser (Playwright Chromium DPR 1, Vite dev server, every `/api/**` mocked, writes refused and recorded) at 1440x900 and 360x740 | 84/84 on `d3aefc2` (74 checks plus, after re-QG R-3, an element-level clipping check per section and width; a control run that re-injects the pre-R-1 rules fails it at 360px audit, as expected): all five sections render with no horizontal overflow or clipped element; provider cards; read-only Claude panel; unqualified Claude in Recovery opening the paid dialog with focus inside, Escape closes; audit search/filter with no request; inert background and scroll lock; Tab trapped in the dialog; focus back on Activate; five section links with a visible focus ring; WCAG AA text contrast in every section; no write sent; no page error |

Browser evidence is MOCK only and does not establish provider interoperability, Live behaviour
or answer quality. Screenshots and the harness are in the session scratchpad (not tracked).

## Independent Quality Gate

- `D100_PHASES_2_4_QUALITY_GATE.md`: PASS on `3b308c1`; Minor F-1, F-2 (recommended), Info F-3
  to F-5. M-1, M-2, I-1, D3, D5 and D6 closed; D4 already closed; D2 open (out of scope).
- `D100_PHASES_2_4_REQG.md`: on `a7e8e31`, F-1 and F-2 fixed; PASS WITH MINOR FIXES for R-1
  (phone audit cards clipped by the app-wide 720px scroll-table minimum, present since
  `3b308c1`), Info R-2 to R-4.
- `D100_PHASES_2_4_REQG2.md`: PASS on `d3aefc2`; R-1 and R-2 closed, R-3 addressed, no Blocker,
  Major or Minor finding remains.

The gate reports are copied here unchanged from the reviewer's output.

## Open and deferred

- D2 (inspector-only remote details) stays open; it was not in the assigned debt scope.
- F-3 (Info): `isolate()` covers elements present when a dialog opens; a banner mounted while it is
  open is not inert. F-4 (Info): the console form rule also restyles the Phase 1 forms (checked
  in the MOCK browser only). R-4 (Info): the harness's mock header shows "undefined Sandbox".
- HR key entry and HR-editable Claude limits stay deferred: they need new backend authority.
- Publication (push, PR) awaits owner authorisation.
