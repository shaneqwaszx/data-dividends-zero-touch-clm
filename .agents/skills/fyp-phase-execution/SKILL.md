---
name: fyp-phase-execution
description: "Use when implementing an explicitly assigned bounded Data Dividends FYP feature, phase, or remediation task."
---

# FYP Phase Execution

Execute exactly one assigned bounded feature, phase, or remediation task. Treat
`AGENTS.md` as global authority. A matching active planner handoff under
`.ai-pipeline/001_planner/` is the scope authority for a phase or remediation; otherwise
the explicit task supplies the bounded goal and acceptance criteria.

This skill owns Stage 1 (stable implementation) of the five-stage lifecycle in
`docs/DEVELOPMENT_WORKFLOW.md`, and Stage 1 remediation after a non-`PASS` gate. It ends
at a stable candidate; Stage 2 integration and acceptance belong to
`integration-safe-development`.

## Establish the work boundary

1. Inspect the current branch, HEAD, staged files, tracked changes, and untracked files.
   Preserve pre-existing work and do not assume the branch name authorizes a phase.
2. Classify the assignment as a bounded feature/task, phase, or remediation. For a phase
   or remediation, select its matching planner handoff. If the assigned scope cannot be
   matched unambiguously, stop the affected work instead of choosing by filename recency.
3. Follow the mandatory `AGENTS.md` loading policy: read the constitution in full,
   classify the change, run `scripts/dev_context.py --change-class <CLASS>` for every
   class, and read each emitted Tier 1 reference/section before relevant contracts,
   decisions, open questions, skills, current owning source/tests, the assigned planner
   when one exists, and the nearest relevant accepted gate/report. Unknown/ambiguous work uses `--full`;
   additional role files and historical reports remain Tier 2, retrieved only for a
   named unanswered question.
4. Extract the goal, acceptance criteria, explicit non-goals, dependencies, unresolved
   sponsor questions, and required checks from the explicit task and any applicable
   planner. Do not convert later-phase readiness into authority to start that phase.
5. Record the canonical task-start capability/resource preflight from
   `docs/DEVELOPMENT_WORKFLOW.md`: current-session tools/plugins and effective
   permissions, required runtimes, relevant browser/database/lifecycle availability,
   reserved ports/shared resources, and the exact claim blocked by any missing
   prerequisite. Tool choice cannot waive the change-class verification matrix.
6. Prepare a compact handoff/scope map with worktree, branch, `BASE_SHA`, canonical
   owners/write boundaries, integration surfaces, adverse cases, evidence identities,
   unresolved authority and next authorized action. Keep current source, tested behavior
   and independently reviewed content distinct.

## Execute the task

1. Inspect the existing implementation and tests before editing.
2. Keep changes small and task-bounded. Do not silently invent a business rule or
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

## Reflect and remediate before integrated acceptance

1. Inspect the complete task diff, including task-owned new files, against every approved
   acceptance criterion and explicit non-goal.
2. Challenge the relevant failure, stale-state, authorization, restart and replay paths.
   Use a narrow specialist falsification review only when risk justifies it; do not impose
   an exhaustive adversarial ceremony on a trivial edit.
3. Reproduce a suspected defect with a focused test or concrete evidence before changing
   the design. Apply the smallest in-scope remediation and rerun the affected focused
   checks after the final change.
4. Stop after two unsuccessful repair cycles for the same underlying design problem by
   default. Escalate the design or authority question instead of looping or widening
   scope.
5. Report self-review as implementer evidence only. Never label it independent QG PASS.

## Verify and hand off

1. Iterate with focused checks that directly exercise the changed behavior and its
   adverse paths, plus lint/type/whitespace checks for touched files. Do not run complete
   repository suites on every iteration; the complete applicable change-class set runs
   once in Stage 2 on the integrated candidate. Run a broader check early only to
   diagnose a suspected cross-cutting failure. Whitespace/hygiene must include
   task-owned untracked files as well as tracked changes. Report skipped, unavailable,
   and failed checks accurately, using the workflow's
   reproducible-defect/missing-infrastructure/stale-evidence/unresolved-authority
   classifications.
2. Recheck the diff for scope creep, secrets, confidential artefacts, and unrelated
   edits.
3. Report a stable candidate in one compact handoff: branch/repository state, files
   changed, behavior implemented, focused checks and exact results, current/tested
   revision identities, decisions/assumptions, blockers/risks, and the next authorized
   action (normally Stage 2 integration and acceptance).
4. Do not commit, push, merge, or change branches unless explicitly instructed.
5. End after the assigned task. Never automatically begin the next phase, even when a
   gate or report says it is ready.
