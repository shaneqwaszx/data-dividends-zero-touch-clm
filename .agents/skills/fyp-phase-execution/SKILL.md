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
3. Follow the mandatory `AGENTS.md` loading order: `AGENTS.md`,
   `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`,
   `docs/DEVELOPMENT_WORKFLOW.md`, relevant contracts/decisions/open questions,
   applicable repository skills, then current owning source and tests. After that chain,
   read the assigned planner handoff and nearest relevant accepted gate/report.
   `docs/PROJECT_CONTEXT.md`, `docs/CODEX_WORKFLOW.md`, role files and historical reports
   are additional context only when the current task needs them.
4. Extract the goal, acceptance criteria, explicit non-goals, dependencies, unresolved
   sponsor questions, and required checks. Do not convert later-phase readiness into
   authority to start that phase.
5. Record the canonical task-start capability/resource preflight from
   `docs/DEVELOPMENT_WORKFLOW.md`: current-session tools/plugins and effective
   permissions, required runtimes, relevant browser/database/lifecycle availability,
   reserved ports/shared resources, and the exact claim blocked by any missing
   prerequisite. Tool choice cannot waive the change-class verification matrix.
6. Prepare a compact handoff/scope map with worktree, branch, `BASE_SHA`, canonical
   owners/write boundaries, integration surfaces, adverse cases, evidence identities,
   unresolved authority and next authorized action. Keep current source, tested behavior
   and independently reviewed content distinct.

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

## Reflect and remediate before independent review

1. Inspect the complete task diff, including task-owned new files, against every approved
   acceptance criterion and explicit non-goal.
2. Challenge the relevant failure, stale-state, authorization, restart and replay paths.
   Use a narrow specialist falsification review only when risk justifies it; do not impose
   an exhaustive adversarial ceremony on a trivial edit.
3. Reproduce a suspected defect with a focused test or concrete evidence before changing
   the design. Apply the smallest in-scope remediation and rerun affected checks after the
   final change.
4. Stop after two unsuccessful repair cycles for the same underlying design problem by
   default. Escalate the design or authority question instead of looping or widening
   scope.
5. Report self-review as implementer evidence only. Never label it independent QG PASS.

## Verify and hand off

1. Run every relevant configured backend, frontend, type/lint, contract, regression,
   dependency-integrity, secret, and whitespace check required by the planner and
   AGENTS.md. Whitespace/hygiene must include task-owned untracked files as well as
   tracked changes. Report skipped, unavailable, and failed checks accurately, using the
   workflow's reproducible-defect/missing-infrastructure/stale-evidence/unresolved-authority
   classifications.
2. Recheck the diff for scope creep, secrets, confidential artefacts, and unrelated
   edits.
3. Report branch/repository state, files changed, behavior implemented, checks and exact
   results, current/tested/reviewed revision identities, decisions/assumptions,
   blockers/risks, and the recommended next authorized action.
4. Do not commit, push, merge, or change branches unless explicitly instructed.
5. End after the assigned phase. Never automatically begin the next phase, even when a
   gate or report says it is ready.
