# Codex Workflow

## Control model

ChatGPT acts as the project planner/advisor.

Codex acts as the execution environment.

Use one bounded phase/task at a time.

## Pipeline

1. Planner handoff defines scope and acceptance criteria.
2. Contract Analyst inspects sponsor/API artefacts when contracts are involved.
3. Builder implements only the approved task.
4. Tester verifies behaviour and edge cases.
5. Reviewer checks correctness, maintainability, and scope creep.
6. Security Reviewer is used whenever auth, secrets, PII/KYC, external APIs, or deployment boundaries are touched.
7. Human reviews results before merge.

## Parallelism

Read-only analysis/review agents may run in parallel.

Avoid having multiple coding agents edit the same files at the same time.

## Branching

- `main` = accepted work only
- phase branches = `phase/00-foundation`, `phase/01-vertical-slice`, etc.
- Codex must not merge to `main` without human instruction.

## Handoff

After each Codex task, paste the completion report back into the ChatGPT planning conversation before starting the next major phase.
