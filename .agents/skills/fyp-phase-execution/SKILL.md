---
name: fyp-phase-execution
description: "Execute one explicitly assigned Data Dividends FYP phase or remediation task from planner handoff through implementation, verification, and completion reporting. Use for bounded project feature work where Codex must establish the branch and phase, preserve CLM architecture and security constraints, and stop before the next phase."
---

# FYP Phase Execution

Execute exactly one assigned phase or remediation task. Treat AGENTS.md as the global
authority and the matching active planner handoff under .ai-pipeline/001_planner/ as
the current phase scope authority.

## Establish the work boundary

1. Inspect the current branch, HEAD, staged files, tracked changes, and untracked files.
   Preserve pre-existing work and do not assume the branch name authorizes a phase.
2. Identify the phase from the user's assignment, then select its matching planner
   handoff. Include a remediation handoff when the task is remediation. If the assigned
   scope cannot be matched unambiguously, stop the affected work instead of choosing a
   phase by filename recency.
3. Read, in order:
   - AGENTS.md;
   - docs/PROJECT_CONTEXT.md and docs/CODEX_WORKFLOW.md;
   - the assigned planner handoff;
   - the nearest relevant final quality-gate report under .ai-pipeline/reports/;
   - relevant role files, architecture, contract, decision, and open-question documents.
4. Extract the goal, acceptance criteria, explicit non-goals, dependencies, unresolved
   sponsor questions, and required checks. Do not convert later-phase readiness into
   authority to start that phase.

## Execute the phase

1. Inspect the existing implementation and tests before editing.
2. Keep changes small and phase-bounded. Do not silently invent a business rule or
   resolve contradictory evidence. Record the issue and stop the dependent portion.
3. Preserve the repository architecture:
   - access external systems through connector/service interfaces;
   - keep source payload -> canonical internal model -> target mapping;
   - keep mock and live implementations replaceable without business-logic changes;
   - keep deterministic business calculations testable and human review available for
     exceptions.
4. Preserve security boundaries. Never expose or track credentials, raw sponsor
   artefacts, KYC/PII, raw external payloads, or private error details.
5. Implement tests with each meaningful behavior change. Update only documentation
   affected by the assigned work, including explicit assumptions and unresolved items.

## Verify and hand off

1. Run every relevant configured backend, frontend, type/lint, contract, regression,
   dependency-integrity, secret, and whitespace check required by the planner and
   AGENTS.md. Report skipped, unavailable, and failed checks accurately.
2. Recheck the diff for scope creep, secrets, confidential artefacts, and unrelated
   edits.
3. Report branch/repository state, files changed, behavior implemented, checks and exact
   results, decisions/assumptions, blockers/risks, and the recommended next human action.
4. Do not commit, push, merge, or change branches unless explicitly instructed.
5. End after the assigned phase. Never automatically begin the next phase, even when a
   gate or report says it is ready.
