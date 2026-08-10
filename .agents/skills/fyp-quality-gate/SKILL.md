---
name: fyp-quality-gate
description: "Run the independent combined quality gate for a completed Data Dividends FYP phase. Use when Codex must review contract/integration behavior, tests, code and architecture, security, and adversarial failure paths; write PHASE_XX_QUALITY_GATE.md; issue PASS, PASS WITH MINOR FIXES, or FAIL; and state next-phase readiness without implementing fixes."
---

# FYP Quality Gate

Review independently. Make no implementation, test, configuration, or ordinary
documentation fixes during the gate.

## Establish evidence and write boundary

1. Confirm the phase from the explicit task and matching planner handoff; do not infer it
   from the highest phase number. Inspect the branch, HEAD, full diff, staged files, and
   untracked files.
2. Read AGENTS.md, project context, workflow, the current planner and remediation
   handoffs, the preceding gate, relevant role files, architecture/contracts, decisions,
   open questions, and changed tests/code.
3. Remain read-only except for exactly
   .ai-pipeline/reports/PHASE_XX_QUALITY_GATE.md. Run checks without writing caches or
   build output into the repository where configurable. Do not install fixes or edit
   reviewed artifacts.

## Run the combined review

Assess each current-phase acceptance criterion through these workstreams:

1. Contract and integration: verify evidence authority, schemas/mappings, connector
   boundaries, mock claims, quarantines, and unresolved dependencies.
2. Testing: run the configured checks and targeted tests; verify happy, review,
   failure, contract, and regression paths.
3. Code and architecture: inspect correctness, maintainability, coupling, state
   transitions, error handling, test depth, and scope creep.
4. Security: inspect secrets, auth, TLS, external data, KYC/PII, logging, browser
   projection, sponsor artefacts, and safe errors.
5. Adversarial testing: challenge malformed/hostile inputs, unexpected exceptions,
   downstream call stopping, terminal-state integrity, isolation, and false-success
   claims.

Do not treat an authored test alone as proof; inspect implementation and obtain focused
execution evidence where practical.

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

State next-phase readiness explicitly and separately from real ACRA/GoldTier readiness.
Do not begin the next phase and do not implement review findings.

Use references/report-template.md when writing the sole report file.
