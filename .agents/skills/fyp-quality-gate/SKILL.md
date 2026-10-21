---
name: fyp-quality-gate
description: "Run the independent combined quality gate for a completed Data Dividends FYP phase or bounded governance change. Use when Codex must review contract/integration behavior, tests, code or instructions and architecture, security, and adverse failure paths; write the assigned gate report; issue PASS, PASS WITH MINOR FIXES, or FAIL; and state readiness without implementing fixes."
---

# FYP Quality Gate

Review independently. Make no implementation, test, configuration, or ordinary
documentation fixes during the gate.

This is Stage 3 of the five-stage lifecycle in `docs/DEVELOPMENT_WORKFLOW.md`. Review
the exact integrated candidate produced by Stage 2, including risks the latest-main
integration introduced. The reviewer must not have authored or remediated the reviewed
content. If no independent reviewer is available, record `AWAITING_INDEPENDENT_QG`;
never substitute self-review.

## Establish evidence and write boundary

1. Confirm the phase or governance change from the explicit task and matching planner
   handoff/assignment; do not infer it from the highest phase number. Inspect the branch,
   HEAD, full diff, staged files, and untracked files.
2. Read AGENTS.md, project context, workflow, the current planner and remediation
   handoffs, the preceding gate, relevant role files, architecture/contracts, decisions,
   open questions, and changed tests/code.
3. Remain read-only except for exactly the assigned report path. A phase defaults to
   `.ai-pipeline/reports/PHASE_XX_QUALITY_GATE.md`; a governance task uses its explicitly
   assigned report name. Run checks without writing caches or build output into the
   repository where configurable. Do not install fixes or edit reviewed artifacts.
4. Record the frozen reviewed-content identity: branch/HEAD, base, complete reviewed path
   set (including task-owned new files), and a deterministic diff/tree identity when
   available. If implementation/instruction content changes during the gate, stop the
   verdict and require a fresh review of the changed scope. The reviewer may write only
   its assigned report and must not change acceptance criteria.
5. Confirm the current session can run each required check. Classify absent prerequisites
   as missing infrastructure and name only the dependent claim they block; never borrow
   tool availability or evidence from another chat.

## Run the combined review

Assess each current-phase acceptance criterion through these workstreams:

1. Contract and integration: verify evidence authority, schemas/mappings, connector
   boundaries, mock claims, quarantines, and unresolved dependencies.
2. Testing: verify that each Stage 2 result matches the frozen content identity and
   environment and is complete; reuse valid evidence rather than mechanically repeating
   it. Run targeted and adversarial tests yourself, plus any check whose evidence is
   missing, stale, partial, inconsistent, or doubtful. Verify happy, review, failure,
   contract, and regression paths and the quality of the tests themselves.
3. Code and architecture: inspect correctness, maintainability, coupling, state
   transitions, error handling, test depth, and scope creep.
4. Security: inspect secrets, auth, TLS, external data, KYC/PII, logging, browser
   projection, sponsor artefacts, and safe errors.
5. Adversarial testing: challenge malformed/hostile inputs, unexpected exceptions,
   downstream call stopping, terminal-state integrity, isolation, and false-success
   claims.

Do not treat an authored test or a Testing-role report alone as proof; inspect the
implementation and obtain focused execution evidence where practical. The gate stays
substantive: approving a test report without independent inspection is not a review.

Use actual runtime evidence when the affected surface requires it: configured
Playwright plus real HTTP/process behavior for browser claims, guarded physical Mongo
for driver/server persistence claims, the lifecycle harness for startup/process claims,
authoritative GitHub observations for remote PR/CI state, and official installed-version
documentation plus local execution for consequential framework behavior. Derive test
inventory from the current owned suites and record collected/executed counts as
revision-specific evidence, never permanent constants.

Check whitespace and hygiene across tracked changes and every task-owned new file. Plain
`git diff --check` does not cover untracked Markdown. Keep reproducible defects, missing
infrastructure, stale evidence and unresolved sponsor authority separate; one missing
lane blocks its dependent claim rather than erasing unrelated verified evidence.

## Classify findings and decide the gate

- Classify a bug when current behavior violates AGENTS.md, the current planner, an
  accepted contract/invariant, or truthful user-visible status.
- Classify accepted technical debt only when the planner/gate explicitly permits the
  limitation and current acceptance remains satisfied. Do not use that label to excuse a
  current defect.
- Classify a current blocker when it prevents a current acceptance criterion or safe
  phase completion. Classify a later sponsor dependency when it affects only an
  explicitly later/non-goal capability. State the two separately.

Use one result:

- PASS: all current acceptance criteria verified; no required fix remains.
- PASS WITH MINOR FIXES: acceptance is substantially met and only bounded, low-risk,
  non-security, non-contract, non-false-success corrections remain. List them explicitly.
- FAIL: any current critical/high-risk defect, unverified required criterion, unsafe
  behavior, material contract error, false success, or phase-scope violation remains.

The independent verdict applies only to the frozen reviewed content and recorded
evidence revisions. Self-review, a prior gate on another tree, or a report authored by
the implementer cannot supply independence. A non-`PASS` result returns to bounded
remediation; the recheck reviews the corrected delta and the evidence it invalidated,
and reuses unchanged valid evidence instead of requiring a new full-suite run.

For a phase gate, state next-phase readiness explicitly and separately from real
ACRA/GoldTier readiness. For a governance gate, state only governance/publication
readiness and do not invent product-phase readiness. Do not begin another phase and do
not implement review findings.

Use `references/report-template.md` for a phase. For a governance task, adapt the same
acceptance/evidence/finding/verdict/Git-status structure without inventing phase
readiness or product claims.
