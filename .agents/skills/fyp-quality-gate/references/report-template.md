# Phase XX quality-gate report template

Write the report to `.ai-pipeline/reports/PHASE_XX_QUALITY_GATE.md` and replace `XX`
with the reviewed phase number.

## Required structure

1. **Executive Result** — `PASS`, `PASS WITH MINOR FIXES`, or `FAIL`, with a concise
   reason and current-phase consequence.
2. **Phase Acceptance Checklist** — one row per planner requirement with result and
   direct evidence.
3. **Contract and Integration Findings** — findings by severity, evidence authority,
   quarantines, and current versus later sponsor dependencies.
4. **Tester and Adversarial Findings** — commands, exact results, skipped/unavailable
   checks, failure injection, terminal states, call stopping, false-success checks, and
   regressions.
5. **Code and Architecture Review** — findings by severity plus scope, coupling,
   maintainability, and accepted technical debt.
6. **Security Review** — findings by severity, evidence, containment, and deferred
   hardening.
7. **Required Fixes** — current bugs/blockers only; keep accepted technical debt and
   later dependencies separate.
8. **Readiness** — state next-phase readiness explicitly. State live ACRA verification
   and real GoldTier integration readiness separately when applicable. Readiness does
   not authorize starting another phase.
9. **Git Status** — branch, HEAD, tracked/untracked/staged state, report-only modification
   statement, and confirmation that no implementation fix, commit, push, merge, or next
   phase occurred.

Distinguish an unexecuted external smoke test from implementation readiness. Include
exact evidence for failed or unavailable checks and never convert missing verification
into a pass.
